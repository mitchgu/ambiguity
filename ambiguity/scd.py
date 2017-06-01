"""A simple version of Chrome Webdriver with special features for ambiguity"""
import re
from time import sleep
import warnings

from PyPDF2 import PdfFileMerger
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from ambiguity.utils import Timeout


class SimpleChromeDriver(webdriver.Chrome):
    """A Chrome webdriver with a simpler API and additional methods"""

    # pylint: disable=super-init-not-called
    def __init__(self, download_dir, profile_dir):
        self.download_dir = download_dir
        self.profile_dir = profile_dir
        self.chrome_options = webdriver.ChromeOptions()
        prefs = {"download.default_directory": str(download_dir.absolute())}
        self.chrome_options.add_experimental_option("prefs", prefs)
        self.chrome_options.add_argument(
            "user-data-dir=" + str(profile_dir.absolute()))
        self.active = False

    def start(self):
        """Start the webdriver. Useful for deferring this past construction"""
        if not self.active:
            super().__init__(chrome_options=self.chrome_options)
            self.active = True

    def quit(self):
        """Quit the webdriver."""
        if self.active:
            super().quit()
            self.active = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.quit()

    def find(self, selector, idx=0):
        """Find the element at position idx that matches the CSS selector"""
        return self.find_all(selector)[idx]

    def find_all(self, selector):
        """Return a list of all elements matching the CSS selector"""
        return self.find_elements_by_css_selector(selector)

    def fill_field(self, selector, value):
        """Type the value into the element matching the CSS selector"""
        field = self.find(selector)
        field.clear()
        field.send_keys(value)

    @staticmethod
    def is_stale(element):
        """Checks if element is stale"""
        try:
            element.is_selected()
            return False
        except StaleElementReferenceException:
            return True

    def wait_on_ec(self, ec):
        """Wait for a given expected condition and return the element"""
        wait = WebDriverWait(self, 10)
        return wait.until(ec)

    def wait_till_clickable(self, selector):
        """Wait till the 1st element matching the CSS selector is clickable"""
        return self.wait_on_ec(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))

    def wait_till_visible(self, selector):
        """Wait till the 1st element matching the CSS selector is visible"""
        return self.wait_on_ec(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))

    def wait_till_frame(self, frame_name):
        """Wait till the given frame is available, then switch to it"""
        return self.wait_on_ec(
            EC.frame_to_be_available_and_switch_to_it(frame_name))

    def scroll_to(self, element):
        """move to element then click it"""
        self.execute_script("arguments[0].scrollIntoView();", element)
        return element

    def clear_download_glob(self, dl_glob):
        """Delete all downloads matching the given file glob"""
        for path in self.download_dir.glob(dl_glob):
            path.unlink()

    def wait_for_download(self, dl_glob):
        """Wait for a download matching the given glob, return its Path"""
        with Timeout(error_message="error downloading file " + dl_glob):
            while not list(self.download_dir.glob(dl_glob)):
                sleep(0.1)
            return list(self.download_dir.glob(dl_glob))[0]

    def print_to_pdf(self, fname, preview_exists=False):
        """Print the current window to a pdf file"""
        original_window_handle = self.current_window_handle
        self.clear_download_glob("print*.pdf")

        def switch_to_print_preview():
            """Switch to the print preview window, return whether successful"""
            for handle in self.window_handles[::-1]:
                self.switch_to_window(handle)
                for _ in range(100):
                    try:
                        if (self.find("html").get_attribute("id") ==
                                "print-preview"):
                            return True
                    except StaleElementReferenceException:
                        continue
                    break
                else:
                    raise RuntimeError("Could not find print preview page")
            return False

        if not preview_exists:
            self.execute_script("setTimeout(window.print, 0);")

        with Timeout(error_message="could not find an open print preview"):
            while switch_to_print_preview() is False:
                sleep(0.25)

        # Pull the pdf url from the print preview dialog
        src = self.wait_till_visible("iframe").get_attribute("src")
        print_url = re.compile(r"chrome://print/([0-9]+)/0/print\.pdf")
        pdf_id = print_url.search(src).group(1)

        # Keep downloading pages until they're empty
        pdf_pages = []
        while True:
            pageno = len(pdf_pages)
            self.get("chrome://print/{}/{}/print.pdf".format(pdf_id, pageno))
            dl_path = self.wait_for_download("print.pdf")
            dest_path = dl_path.with_name("page{}.pdf".format(pageno))
            if dl_path.stat().st_size > 2000:  # 2KB
                dl_path.rename(dest_path)
                pdf_pages.append(dest_path)
            else:
                dl_path.unlink()
                break

        # Merge them together
        merger = PdfFileMerger(strict=False)
        for page in pdf_pages:
            merger.append(page.open("rb"))
            page.unlink()
        fname.parent.mkdir(parents=True, exist_ok=True)
        with fname.open("wb") as fout:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                merger.write(fout)

        # Close dialog and return to original screen
        self.wait_till_clickable("button.cancel").click()
        self.switch_to_window(original_window_handle)

    def reset(self):
        """Clear all windows and cookies, leaving a new tab window"""
        while len(self.window_handles) > 1:
            self.switch_to_window(self.window_handles[-1])
            self.close()
        self.switch_to_window(self.window_handles[0])
        self.get("chrome://newtab")
        self.delete_all_cookies()
