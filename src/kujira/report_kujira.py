"""
usage: python3 report_kujira.py <walletaddress> [--format all|cointracking|koinly|..]
Prints transactions and writes CSV(s) to _reports/KUJIRA*.csv
"""

import logging
import pprint

from kujira.config_kujira import localconfig
from kujira.progress_kujira import SECONDS_PER_PAGE, ProgressKujira
from common import report_util
from common.Cache import Cache
from common.Exporter import Exporter
from common.ExporterTypes import FORMAT_DEFAULT
from settings_csv import TICKER_KUJIRA, KUJIRA_NODE
import kujira.processor
import common.ibc.api_lcd


def main():
    wallet_address, export_format, txid, options = report_util.parse_args(TICKER_KUJIRA)

    if txid:
        _read_options(options)
        exporter = txone(wallet_address, txid)
        exporter.export_print()
        if export_format != FORMAT_DEFAULT:
            report_util.export_format_for_txid(exporter, export_format, txid)
    else:
        exporter = txhistory(wallet_address, options)
        report_util.run_exports(TICKER_KUJIRA, wallet_address, exporter, export_format)


def _read_options(options):
    report_util.read_common_options(localconfig, options)
    logging.info("localconfig: %s", localconfig.__dict__)


def wallet_exists(wallet_address):
    return common.ibc.api_lcd.LcdAPI(KUJIRA_NODE).account_exists(wallet_address)


def txone(wallet_address, txid):
    elem = common.ibc.api_lcd.LcdAPI(KUJIRA_NODE).get_tx(txid)

    print("Transaction data:")
    pprint.pprint(elem)

    exporter = Exporter(wallet_address, localconfig, TICKER_KUJIRA)
    txinfo = kujira.processor.process_tx(wallet_address, elem, exporter)
    txinfo.print()
    return exporter


def estimate_duration(wallet_address, options):
    max_txs = localconfig.limit
    return SECONDS_PER_PAGE * common.ibc.api_lcd.get_txs_pages_count(KUJIRA_NODE, wallet_address, max_txs)


def txhistory(wallet_address, options):
    # Configure localconfig based on options
    _read_options(options)
    if localconfig.cache:
        localconfig.ibc_addresses = Cache().get_ibc_addresses()
        logging.info("Loaded ibc_addresses from cache ...")

    max_txs = localconfig.limit
    progress = ProgressKujira()
    exporter = Exporter(wallet_address, localconfig, TICKER_KUJIRA)

    # Fetch count of transactions to estimate progress more accurately
    count_pages = common.ibc.api_lcd.get_txs_pages_count(KUJIRA_NODE, wallet_address, max_txs, debug=localconfig.debug)
    progress.set_estimate(count_pages)

    # Fetch transactions
    elems = common.ibc.api_lcd.get_txs_all(KUJIRA_NODE, wallet_address, progress, max_txs, debug=localconfig.debug)

    progress.report_message(f"Processing {len(elems)} transactions... ")
    kujira.processor.process_txs(wallet_address, elems, exporter)

    if localconfig.cache:
        Cache().set_ibc_addresses(localconfig.ibc_addresses)
    return exporter


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()