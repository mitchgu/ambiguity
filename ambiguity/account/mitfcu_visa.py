"""Account class for MITFCU Visa credit cards"""
import datetime
from time import sleep

from ambiguity import StatementDate
from ambiguity.account import Account
from ambiguity.utils import Timeout


class MITFCUVisa(Account):
    """A concrete Account class for MITFCU Visa accounts"""

    PULL_FMTS = {"pdf", "csv", "xlsx", "qfx", "ofx"}
    FCU_VISA_AUX_FMTS = {"csv", "xlsx", "qfx", "ofx"}
    BASE_URL = "https://www.mitfcu.org"
    ESTMT_URL = "https://mitfcu.mycardinfo.com/estatementenroll.aspx"
    LOGOUT_URL = "https://www.mitfcu2.org/tob/live/usp-core/app/logout"
    TRANSACTIONS_URL = "https://mitfcu.mycardinfo.com/AccountTransactions.aspx"
    CURRENT_JS = (
        'WebForm_DoPostBackWithOptions('
        'new WebForm_PostBackOptions(''"ctl00$MainContent$lbCurrentActivity", '
        '"", true, "", "", false, true))')
    BASE_DL_URL = "https://mitfcu.mycardinfo.com/downloadtransactions.ashx"
    DL_URLS = {
        "xlsx": BASE_DL_URL + "?m=excel",
        "csv": BASE_DL_URL + "?m=csv",
        "qfx": BASE_DL_URL + "?m=qfx",
        "ofx": BASE_DL_URL + "?m=ofx",
    }
    SELECTORS = {
        "login_frame": "iframe[title='Online Banking Login']",
        "username": "input#userid",
        "password": "input#password",
        "login": "button[type=submit]",
        "account_link": "a[title='XXXXXXXXXXXX{} *{}']",
        "mycardinfo_home": "#user-summary",
        "pdf_stmt_link": "table.estatements-list a",
        "date_picker": "#selected-date",
        "stmt_choice": "li.previous-statements a, li.most-recent-statements a",
        "overlay": "#transactions-container .animated-overlay",
    }

    def __init__(self, last_four_digits, **kwargs):
        self.last_four_digits = last_four_digits
        super().__init__(**kwargs)

    # pylint: disable=too-many-branches, too-many-statements
    def do_pull(self, scd, credentials, statements, pull_current=False):
        # Login
        scd.get(self.BASE_URL)
        scd.switch_to.frame(scd.find(self.SELECTORS["login_frame"]))
        scd.fill_field(self.SELECTORS["username"], credentials[0])
        scd.fill_field(self.SELECTORS["password"], credentials[1])
        scd.find(self.SELECTORS["login"]).click()

        # Navigate to mycardinfo
        scd.wait_till_clickable(self.SELECTORS["account_link"].format(
                self.last_four_digits,
                self.last_four_digits)).click()
        scd.close()
        scd.switch_to.window(scd.window_handles[0])
        scd.wait_till_visible(self.SELECTORS["mycardinfo_home"])

        pdf_statements = set()
        fcu_visa_aux_statements = dict()
        for sd, fmts in statements.items():
            if "pdf" in fmts:
                pdf_statements.add(sd)
            if self.FCU_VISA_AUX_FMTS & fmts:
                fcu_visa_aux_statements[sd] = self.FCU_VISA_AUX_FMTS & fmts

        if pdf_statements:
            # See which PDF statements are available
            scd.get(self.ESTMT_URL)
            pdfjs = dict()
            for choice in scd.find_all(self.SELECTORS["pdf_stmt_link"]):
                mm, _dd, yyyy = choice.text.split("/")
                sd = StatementDate(yyyy, mm)
                pdfjs[sd] = choice.get_attribute("href")[11:]

            for sd in pdf_statements:
                if sd not in pdfjs:
                    self.log_failed_pull(sd, "pdf")
                    continue
                scd.clear_download_glob("*.pdf")
                scd.execute_script(pdfjs[sd])
                dl_path = scd.wait_for_download("*.pdf")
                self.file_statement(dl_path, sd, "pdf")
                self.log_successful_pull(sd, "pdf")

        if fcu_visa_aux_statements:
            scd.get(self.TRANSACTIONS_URL)
            scd.wait_till_clickable(self.SELECTORS["date_picker"]).click()
            docjs = dict()
            for choice in scd.find_all(self.SELECTORS["stmt_choice"]):
                dt_string = choice.text.split(" - ")[1]
                dt = datetime.datetime.strptime(dt_string, "%b %d, %Y")
                sd = StatementDate.from_datetime(dt)
                docjs[sd] = choice.get_attribute("href")[11:]
            scd.wait_till_clickable(self.SELECTORS["date_picker"]).click()

            for sd, fmts in fcu_visa_aux_statements.items():
                if sd not in docjs:
                    for fmt in fmts:
                        self.log_failed_pull(sd, fmt)
                    continue
                scd.execute_script(docjs[sd])
                with Timeout(error_message="error switching MITFCU dates"):
                    while scd.find(self.SELECTORS["overlay"]).is_displayed():
                        sleep(0.1)
                for fmt in fmts:
                    scd.clear_download_glob("*." + fmt)
                    scd.get(self.DL_URLS[fmt])
                    dl_path = scd.wait_for_download("*." + fmt)
                    self.file_statement(dl_path, sd, fmt)
                    self.log_successful_pull(sd, fmt)

        # Logout
        scd.get(self.LOGOUT_URL)
