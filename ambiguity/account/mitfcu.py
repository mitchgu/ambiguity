"""Account class for MITFCU"""
from time import sleep
from ambiguity import StatementDate
from ambiguity.account import Account


class MITFCU(Account):
    """A concrete Account class for MITFCU accounts"""

    PULL_FMTS = {"csv", "pdf"}
    BASE_URL = "https://www.mitfcu.org"
    LOGOUT_URL = "https://www.mitfcu2.org/tob/live/usp-core/app/logout"
    CSV_URL = (
        "https://estatements.cowww.com/cowww/DocumentServer/"
        "XmlStatementDownload?AppID=585"
        "&DocumentID={docid}"
        "&AppViewerID=1939"
        "&SubAccount={subaccount}"
        "&Style=CSV"
        "&Description={description}")
    PRINT_URL = (
        "https://estatements.cowww.com/cowww/DocumentServer/"
        "ViewDoc?AppID=585"
        "&DocumentID={docid}"
        "&PrimaryKey={docid}"
        "&AppViewerID=1939&"
        "SubAccountID={subaccount}"
        "&SubAccountDescription={description}"
        "&DownloadLink=0"
        "&PrintMode=single")
    SELECTORS = {
        "login_frame": "iframe[title='Online Banking Login']",
        "username": "input#userid",
        "password": "input#password",
        "login": "button[type=submit]",
        "additional_services": "a[aria-label='Additional Services']",
        "e-statements": "a[aria-label='e-Statements']",
        "estmt_btn": "input[type='BUTTON']",
        "cow_frame": "content",
        "viewer_link": "b a",
        "hitlist_frame": "hitlist",
        "hit": "table table table tr.normal a",
        "next_hitlist_js": "parent.build.UIMovePage('hitList',true)",
    }

    def __init__(self, subaccount, description, **kwargs):
        self.subaccount = subaccount
        self.description = description
        super().__init__(**kwargs)

    def do_pull(self, scd, credentials, statements, pull_current=False):
        # Login
        scd.get(self.BASE_URL)
        scd.switch_to.frame(scd.find(self.SELECTORS["login_frame"]))
        scd.fill_field(self.SELECTORS["username"], credentials[0])
        scd.fill_field(self.SELECTORS["password"], credentials[1])
        scd.find(self.SELECTORS["login"]).click()

        # Navigate to E-Statement viewer
        sleep(2)
        try:
            scd.find(self.SELECTORS["additional_services"]).click()
        except IndexError:
            print("Please confirm it's you and save this browser profile")
            print("Press Enter when you're done")
            input()
        scd.find(self.SELECTORS["additional_services"]).click()
        scd.find(self.SELECTORS["e-statements"]).click()

        scd.accept_alert()

        scd.close()
        scd.switch_to.window(scd.window_handles[0])
        scd.wait_till_frame(self.SELECTORS["cow_frame"])
        scd.find(self.SELECTORS["viewer_link"]).click()
        scd.close()
        scd.switch_to.window(scd.window_handles[0])

        # See which statements are available from hitlist sidebar
        docids = dict()
        scd.wait_till_frame(self.SELECTORS["hitlist_frame"])
        while True:
            n_docs = len(docids)
            scd.wait_till_clickable(self.SELECTORS["hit"])
            for choice in scd.find_all(self.SELECTORS["hit"]):
                mm, _dd, yyyy = choice.text.split("/")
                sd = StatementDate(yyyy, mm)
                docids[sd] = choice.get_attribute("href")[-8:-1]
            if len(docids) == n_docs:
                break
            scd.execute_script(self.SELECTORS["next_hitlist_js"])

        for sd, fmts in statements.items():
            for fmt in fmts:
                if sd not in docids:
                    self.log_failed_pull(sd, fmt)
                    continue
                if fmt == "csv":
                    scd.clear_download_glob("*." + fmt)
                    scd.get(self.CSV_URL.format(
                        docid=docids[sd],
                        subaccount=self.subaccount,
                        description=self.description))
                    dl_path = scd.wait_for_download("*." + fmt)
                elif fmt == "pdf":
                    scd.get(self.PRINT_URL.format(
                        docid=docids[sd],
                        subaccount=self.subaccount,
                        description=self.description))
                    dl_path = scd.download_dir / "temp.pdf"
                    scd.print_to_pdf(dl_path, True)
                else:
                    self.log_failed_pull(sd, fmt)
                    continue
                self.file_statement(dl_path, sd, fmt)
                self.log_successful_pull(sd, fmt)

        # Logout
        scd.get(self.LOGOUT_URL)
