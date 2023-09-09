import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Union
import logging

import pandas as pd

from scripts.correlation_constants import Security, FredSeries
from scripts.file_reading_funcs import get_validated_security_data


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING for production; DEBUG for development


def define_top_correlations(all_main_securities: Union[List['Security'], List['FredSeries']]) \
        -> Union[List['Security'], List['FredSeries']]:
    num_symbols = 40

    # Define the correlation attributes and their corresponding positive and negative correlation attributes
    correlation_start_dates = ['2010', '2018', '2021', '2022', '2023']

    # Loop through each securities_main security
    for main_security in all_main_securities:
        # Loop through each correlation start_date
        for start_date in correlation_start_dates:
            correlation_dict = main_security.all_correlations.get(start_date, {})

            if len(correlation_dict) == 0:
                continue

            # Sort the symbols by their correlation values in descending and ascending order
            sorted_symbols_desc = sorted(correlation_dict.keys(), key=correlation_dict.get, reverse=True)
            sorted_symbols_asc = sorted(correlation_dict.keys(), key=correlation_dict.get, reverse=False)

            # Add the top num_symbols positively correlated securities to the positive_correlations attribute
            for symbol in sorted_symbols_desc[:num_symbols]:
                correlated_security = Security(symbol)
                correlated_security.set_correlation(correlation_dict[symbol])
                main_security.positive_correlations[start_date].append(correlated_security)

            # Add the top num_symbols negatively correlated securities to the negative_correlations attribute
            for symbol in sorted_symbols_asc[:num_symbols]:
                correlated_security = Security(symbol)
                correlated_security.set_correlation(correlation_dict[symbol])
                main_security.negative_correlations[start_date].append(correlated_security)

            # Set the correlation_dict for the start_date to None
            main_security.all_correlations[start_date] = None

    return all_main_securities


class CorrelationCalculator:
    def __init__(self):
        self.DEBUG = False

    def define_correlation_for_each_year(self, securities_list, symbols, end_date,
                                         source, dl_data, use_ch, use_multiprocessing):

        all_start_dates = ['2023']

        if use_multiprocessing:
            for start_date in all_start_dates:
                self.define_correlations_for_series_list_fast(securities_list, symbols, start_date, end_date, source,
                                                              dl_data, use_ch)
        else:
            for start_date in all_start_dates:
                self.define_correlations_for_series_list(securities_list, symbols, start_date, end_date, source,
                                                         dl_data, use_ch)

        return securities_list

    # def define_correlations_for_series_list_fast(self, all_main_securities: Union[List['Security'], List['FredSeries']],
    #                                              symbols: List[str],
    #                                              start_date: str, end_date:
    #         str, source: str, dl_data: bool, use_ch: bool) -> List['Security']:
    #     if self.DEBUG:
    #         symbols = ['UNH', 'XOM']
    #
    #     symbols = list(set(symbols))  # This DOES change the order of symbols
    #
    #     max_workers = 1 if (dl_data or self.DEBUG) else (multiprocessing.cpu_count() // 4)
    #
    #     with ProcessPoolExecutor(max_workers=max_workers) as executor:
    #         results = executor.map(self.process_symbol, symbols, [start_date] * len(symbols), [end_date] * len(symbols),
    #                                [source] * len(symbols), [dl_data] * len(symbols), [use_ch] * len(symbols))
    #
    #         for symbol, security_data in results:
    #
    #             if security_data is None:  # Check for None before processing
    #                 continue
    #             i = 0
    #
    #             while i < len(all_main_securities):  # Loop to go through all the securities_main Securities
    #
    #                 main_security = all_main_securities[i]
    #
    #                 if isinstance(main_security, Security) and symbol == main_security.symbol:
    #                     i += 1
    #                     continue  # Skips comparison if being compared to itself
    #
    #                 main_security_data = main_security.series_data[start_date]
    #
    #                 correlation_float = self.get_correlation_for_series(main_security_data, security_data)
    #
    #                 if start_date not in main_security.all_correlations:
    #                     main_security.all_correlations[start_date] = {}
    #
    #                 main_security.all_correlations[start_date][symbol] = correlation_float
    #
    #                 i += 1
    #     return all_main_securities

    def define_correlations_for_series_list(self, all_main_securities: Union[List['Security'], List['FredSeries']],
                                            symbols: List[str],
                                            start_date: str, end_date: str, source: str, dl_data: bool, use_ch: bool) \
            -> List['Security']:
        """Main function for calculating the correlations for each Security against a list of other securities"""
        if self.DEBUG:
            symbols = ['AAPL', 'MSFT', 'TSM', 'BRK-A', 'CAT', 'CCL', 'NVDA', 'MVIS', 'ASML', 'GS', 'CLX', 'CHD', 'TSLA',
                       'COST', 'TGT', 'JNJ', 'GOOG', 'AMZN', 'UNH', 'XOM', 'PG', 'TM', 'SHEL', 'META', 'CRM', 'AVGO',
                       'QCOM', 'TXM', 'MA', 'SHOP', 'NOW', 'V', 'SCHW', 'TMO', 'DHR', 'TT', 'UNP', 'PYPL', 'BAC', 'WFC',
                       'TD', 'NU', 'TAK', 'ZTS', 'HCA', 'HON', 'NEE', 'LIN', 'SHW', 'BHP', 'ET', 'LNG', 'E']

        symbols = set(symbols)  # This changes the order of symbols
        all_main_securities_set = set(all_main_securities)

        for symbol in symbols:

            try:
                security_data = get_validated_security_data(symbol, start_date, end_date, source, dl_data, use_ch)
            except AttributeError:  # Better than checking if its None every time
                continue

            for main_security in all_main_securities_set:

                if isinstance(main_security, Security) and symbol == main_security.symbol:
                    continue  # Skips comparison if being compared to itself

                main_security_data_detrended = main_security.series_data_detrended[start_date]

                try:
                    correlation_float = self.get_correlation_for_series(main_security_data_detrended, security_data)
                except TypeError:
                    logger.warning(f'Skipping correlation calculation for {symbol} due to missing data.')
                    continue

                if start_date not in main_security.all_correlations:
                    main_security.all_correlations[start_date] = {}

                main_security.all_correlations[start_date][symbol] = correlation_float

        return all_main_securities

    def get_correlation_for_series(self, main_security_data_detrended: pd.DataFrame, security_data: pd.DataFrame) -> float:
        aligned_main, aligned_symbol = main_security_data_detrended.align(security_data, join='inner', axis=0)

        # After aligning, ensure column names are retained
        aligned_main.columns = main_security_data_detrended.columns
        aligned_symbol.columns = security_data.columns

        correlation = self.compute_correlation(aligned_main['main'], aligned_symbol['symbol'])

        return correlation

    @staticmethod
    def compute_correlation(series_data1: pd.Series, series_data2: pd.Series) -> float:
        return series_data1.corr(series_data2)


if __name__ == '__main__':
    manager = CorrelationCalculator()
    # Call the desired methods on the manager instance
    # manager.define_correlations_for_series_list(...)
