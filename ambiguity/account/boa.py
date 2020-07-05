"""Account class for Bank of America"""
import datetime
from time import sleep

from ambiguity import StatementDate
from ambiguity.account import Account
from ambiguity.utils import Timeout


class BoA(Account):
    """Concrete Account class for Bank of America"""

    PULL_FMTS = {"pdf", "csv", "qfx", "qif", "txt"}
    BOA_AUX_FMTS = {"csv", "qfx", "qif", "txt"}
    BASE_URL = "https://www.bankofamerica.com/"
    LOGOUT_URL = ("https://secure.bankofamerica.com/myaccounts/signoff/"
                  "signoff-default.go")
    SELECTORS = {
        "username": "input[name=onlineId1]",
        "password": "input[name=passcode1]",
        "login": "button#signIn",
        "account_names": "span.AccountName a",
        "dl_modal": "a[name=download_transactions_top]",
        "txn_dropdown": "select#select_txnperiod, select#select_transaction",
        "txn_dropdown_opts": ("select#select_txnperiod option, "
                              "select#select_transaction option"),
        "dl_btn": "a.submit-download",
        "error_box": ".error-message-box",
        "pdf_page": 'a[title="Statements & Documents"]',
        "pdf_stmt": "a.statement-name",
        "pdf_stmt_dates": "td.first.TL_NPI_L2",
        "pdf_dl_link": "div.ui-dialog-content a#menuOption3",
    }

    FMT_SELECTORS = {
        "csv": "option[name=download_file_in_this_format_CSV]",
        "qfx": "option[name=download_file_in_this_format_QFX]",
        "qif": "option[name=download_file_in_this_format_QIF4]",
        "txt": "option[name=download_file_in_this_format_TXT]",
    }

    def __init__(self, last_four_digits, **kwargs):
        self.last_four_digits = last_four_digits
        super().__init__(**kwargs)

    # pylint: disable=too-many-branches, too-many-statements
    def do_pull(self, scd, credentials, statements, pull_current=False):
        scd.get(self.BASE_URL)
        sleep(1)
        scd.fill_field(self.SELECTORS["username"], credentials[0])
        scd.fill_field(self.SELECTORS["password"], credentials[1])
        sleep(0.5)
        scd.wait_till_clickable(self.SELECTORS["login"]).click()

        scd.wait_till_visible(self.SELECTORS["account_names"])
        # import pdb; pdb.set_trace()
        for an in scd.find_all(self.SELECTORS["account_names"]):
            if an.text[-4:] == self.last_four_digits:
                an.click()
                break
        else:
            raise ValueError("No BoA account with last four digits found")

        pdf_statements = set()
        boa_aux_statements = dict()
        for sd, fmts in statements.items():
            if "pdf" in fmts:
                pdf_statements.add(sd)
            if self.BOA_AUX_FMTS & fmts:
                boa_aux_statements[sd] = self.BOA_AUX_FMTS & fmts

        if boa_aux_statements:
            def detect_aux_statements():
                """Scan the activity page for available auxiliary statements"""
                if not scd.find(self.SELECTORS["txn_dropdown"]).is_displayed():
                    scd.wait_till_clickable(self.SELECTORS["dl_modal"]).click()
                other_stmts = dict()
                choices = scd.find_all(self.SELECTORS["txn_dropdown_opts"])[1:]
                for choice in choices:
                    if "Period ending" in choice.text:
                        dt_string = choice.text.strip()[-10:]
                        dt = datetime.datetime.strptime(dt_string, "%m/%d/%Y")
                    else:
                        dt_string = choice.text.strip()
                        dt = datetime.datetime.strptime(dt_string, "%B %d, %Y")
                    sd = StatementDate.from_datetime(dt)
                    other_stmts[sd] = choice
                return other_stmts
            other_stmts = detect_aux_statements()

            for sd, fmts in boa_aux_statements.items():
                if sd not in other_stmts:
                    for fmt in fmts:
                        self.log_failed_pull(sd, fmt)
                    continue
                with Timeout(error_message="could not click on statement"):
                    while not other_stmts[sd].is_displayed():
                        sleep(0.1)
                other_stmts[sd].click()
                for fmt in fmts:
                    scd.clear_download_glob("*." + fmt)
                    scd.wait_till_clickable(self.FMT_SELECTORS[fmt]).click()
                    scd.find(self.SELECTORS["dl_btn"]).click()
                    if scd.is_stale(other_stmts[sd]):
                        # page reloaded, no txns in period
                        for fmt2 in fmts:
                            dl_path = scd.download_dir / ("temp." + fmt2)
                            dl_path.touch()
                            self.file_statement(dl_path, sd, fmt2)
                            self.log_successful_pull(sd, fmt2)
                        other_stmts = detect_aux_statements()
                        break
                    elif not scd.find(
                            self.SELECTORS["txn_dropdown"]).is_displayed():
                        scd.find(self.SELECTORS["dl_modal"]).click()
                    dl_path = scd.wait_for_download("*." + fmt)
                    self.file_statement(dl_path, sd, fmt)
                    self.log_successful_pull(sd, fmt)

        if pdf_statements:
            import pdb; pdb.set_trace()
            # not supported anymore :()
            # pdf_stmts = dict()
            # scd.wait_till_clickable(self.SELECTORS["pdf_page"]).click()
            # scd.wait_till_clickable(self.SELECTORS["pdf_stmt"])
            # choices = scd.find_all(self.SELECTORS["pdf_stmt"])
            # choice_dates = scd.find_all(self.SELECTORS["pdf_stmt_dates"])
            # for i in range(len(choice_dates)):
            #     choice_date = choice_dates[i]
            #     choice = choices[i]
            #     if "Statement" not in choice.text:
            #         continue
            #     dt = datetime.datetime.strptime(choice_date.text, "%m/%d/%Y")
            #     sd = StatementDate.from_datetime(dt)
            #     pdf_stmts[sd] = choice
            # for sd in pdf_statements:
            #     if sd not in pdf_stmts:
            #         self.log_failed_pull(sd, "pdf")
            #         continue
            #     scd.clear_download_glob("*.pdf")
            #     scd.scroll_to(pdf_stmts[sd]).click()
            #     scd.wait_till_clickable(self.SELECTORS["pdf_dl_link"]).click()
            #     dl_path = scd.wait_for_download("*.pdf")
            #     self.file_statement(dl_path, sd, "pdf")
            #     self.log_successful_pull(sd, "pdf")

        # Logout
        scd.get(self.LOGOUT_URL)


class BoAVisa(BoA):
    """Concrete Account class for Bank of America Visa"""

    PULL_FMTS = {"pdf", "csv", "qfx", "qif"}
    BOA_AUX_FMTS = {"csv", "qfx", "qif"}

    FMT_SELECTORS = {
        "csv": "option[name=download_file_in_this_format_COMMA_DELIMITED]",
        "qfx": "option[name=download_file_in_this_format_QFX]",
        "qif": "option[name=download_file_in_this_format_QIF_4_digit]",
    }
