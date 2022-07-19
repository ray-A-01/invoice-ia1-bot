"""Creates and saves invoice for client: IA1."""

from quickbooks import invoices
import sys
import logging
import yaml

__author__ = 'Aniruddha Ray'
__version__ = '1.0.0'

# Reading config file
with open('config.yaml', 'r') as stream:
    config = yaml.safe_load(stream)

# Configuring root logger
logging.basicConfig(
    filename=config['run_log']['filepath'],
    filemode='a',
    level=config['run_log']['level'],
    format='%(asctime)s, %(filename)s, %(funcName)s, %(levelname)s, '
           '%(message)s',
    datefmt='%m/%d/%y %H:%M:%S'
)


def main(invoice_num, customer_name, line_items, due_date, invoice_pdf_path):
    # Getting the access token
    logging.info('Getting access token.')
    access_token = invoices.get_access_token_from_refresh_token()
    if access_token == 'Access token could not be obtained.':
        return 'FAIL: ' + access_token
    logging.info('Token obtained.')

    # Creating invoice in QuickBooks
    line_items_mod = []
    for line in line_items:
        line_items_mod.append([detail for detail in line])
    logging.info('Creating invoice in QuickBooks.')
    invoice_id = invoices.create_invoice(access_token, int(invoice_num),
                                         customer_name, line_items_mod,
                                         due_date)
    if invoice_id == -1:
        return 'FAIL: Invoice could not be created'
    logging.info('Invoice created.')

    # Saving invoice as pdf
    logging.info('Saving invoice as pdf.')
    is_invoice_saved = invoices.get_invoice_pdf(access_token,
                                                invoice_id,
                                                invoice_pdf_path)
    if not is_invoice_saved:
        return 'FAIL: Invoice could not be saved as pdf.'
    logging.info('PDF version saved to file.')

    return 'SUCCESS'


if __name__ == '__main__':
    if len(sys.argv) == 6:
        invoice_num = sys.argv[1]
        customer_name = sys.argv[2]
        line_items = sys.argv[3]
        due_date = sys.argv[4]
        invoice_pdf_path = sys.argv[5]

        main(invoice_num, customer_name, line_items, due_date,
             invoice_pdf_path)
