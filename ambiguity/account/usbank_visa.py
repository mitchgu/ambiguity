"""Account class for MITFCU Visa credit cards"""
import datetime
from time import sleep
from selenium.common.exceptions import TimeoutException

from ambiguity import StatementDate
from ambiguity.account import Account
from ambiguity.utils import Timeout


class USBankVisa(Account):
    """A concrete Account class for MITFCU Visa accounts"""

    PULL_FMTS = {"pdf", "csv", "qfx", "qif"}
    USBANK_AUX_FMTS = {"csv", "qfx", "qif"}
    BASE_URL = "https://usbank.com/"
    LOGOUT_URL = "https://onlinebanking.usbank.com/Auth/LogoutConfirmation"
    SELECTORS = {
        "username": "#aw-personal-id",
        "continue": "#btnContinue",
        "password": "#aw-password",
        "login": "#aw-log-in",
        "stmts_link": "#myaccount_BCCreditCardViewOnlineStatements a",
        "stmt_list": "#DocumentList",
        "stmt_links": "#DocumentList a",
        "dl_xactions": "#DownloadTransactionsLink a",
        "start_date": "#FromDateInput",
        "end_date": "#ToDateInput",
        "dl_format_btn": "#ddlFormatType-button",
        "dl_format_menu": "#ddlFormatType-menu",
        "dl_format_item": "#ddlFormatType-menu a",
        "dl_btn": "#DTLLink",
        "dl_cancel": "#lnkLASCancel",
    }

    def __init__(self, last_four_digits, **kwargs):
        self.last_four_digits = last_four_digits
        super().__init__(**kwargs)

    # pylint: disable=too-many-branches, too-many-statements
    def do_pull(self, scd, credentials, statements, pull_current=False):
        # Login
        scd.get(self.BASE_URL)
        scd.fill_field(self.SELECTORS["username"], credentials[0])
        scd.fill_field(self.SELECTORS["password"], credentials[1])
        scd.wait_till_clickable(self.SELECTORS["login"]).click()
        import pdb; pdb.set_trace()
        try:
            scd.wait_till_clickable(self.SELECTORS["dl_xactions"])
        except TimeoutException:
            print("Please verify your phone via SMS")
            print("Press Enter when you're done")
            input()
            scd.wait_till_clickable(self.SELECTORS["dl_xactions"])

        pdf_statements = set()
        usbank_aux_statements = dict()
        for sd, fmts in statements.items():
            if "pdf" in fmts:
                pdf_statements.add(sd)
            if self.USBANK_AUX_FMTS & fmts:
                usbank_aux_statements[sd] = self.USBANK_AUX_FMTS & fmts

        if usbank_aux_statements:
            scd.wait_till_clickable(self.SELECTORS["dl_xactions"]).click()
            scd.wait_till_visible(self.SELECTORS["start_date"])
            for sd, fmts in usbank_aux_statements.items():
                end_dt = sd.to_datetime(self.statement_day)
                first_of_month = end_dt.replace(day=1)
                previous_month = first_of_month - datetime.timedelta(days=1)
                start_dt = previous_month.replace(day=self.statement_day+1)
                # assume day won't roll over
                print(start_dt.isoformat(), end_dt.isoformat())
                scd.fill_field_slow(self.SELECTORS["start_date"], start_dt.strftime("%m/%d/%Y"))
                scd.fill_field_slow(self.SELECTORS["end_date"], end_dt.strftime("%m/%d/%Y"))

                def ensure_fmt_menu_visible():
                    if not scd.find(self.SELECTORS["dl_format_menu"]).is_displayed():
                        scd.wait_till_clickable(self.SELECTORS["dl_format_btn"]).click()
                        scd.wait_till_visible(self.SELECTORS["dl_format_menu"])
                    return scd.find_all(self.SELECTORS["dl_format_item"])

                for fmt in fmts:
                    import pdb; pdb.set_trace()
                    fmt_items = ensure_fmt_menu_visible()
                    scd.clear_download_glob("*." + fmt)
                    if fmt == "csv":
                        if "CSV" not in fmt_items[1].text:
                            self.log_failed_pull(sd, fmt)
                            continue
                        fmt_items[1].click()
                    elif fmt == "qfx":
                        if "QFX" not in fmt_items[2].text:
                            self.log_failed_pull(sd, fmt)
                            continue
                        fmt_items[2].click()
                    elif fmt == "qif":
                        if "QIF" not in fmt_items[3].text:
                            self.log_failed_pull(sd, fmt)
                            continue
                        fmt_items[3].click()
                    else:
                        self.log_failed_pull(sd, fmt)
                        continue
                    scd.wait_till_clickable(self.SELECTORS["dl_btn"]).click()
                    dl_path = scd.wait_for_download("*." + fmt)
                    self.file_statement(dl_path, sd, fmt)
                    self.log_successful_pull(sd, fmt)
            scd.wait_till_clickable(self.SELECTORS["dl_cancel"]).click()

        if pdf_statements:
            pdf_stmts = dict()
            scd.wait_till_clickable(self.SELECTORS["stmts_link"]).click()
            scd.wait_till_visible(self.SELECTORS["stmt_list"])
            choices = scd.find_all(self.SELECTORS["stmt_links"])
            for c in choices:
                try:
                    dt = datetime.datetime.strptime(c.text, "%B %d, %Y")
                except ValueError:
                    continue
                if abs(dt.day - self.statement_day) < 3:
                    # Assume day won't roll over
                    sd = StatementDate.from_datetime(dt)
                    pdf_stmts[sd] = c
            for sd in pdf_stmts:
                if sd not in pdf_stmts:
                    self.log_failed_pull(sd, "pdf")
                    continue
                scd.clear_download_glob("*.pdf")
                scd.scroll_to(pdf_stmts[sd]).click()
                dl_path = scd.wait_for_download("*.pdf")
                self.file_statement(dl_path, sd, "pdf")
                self.log_successful_pull(sd, "pdf")

        # Logout
        scd.get(self.LOGOUT_URL)
