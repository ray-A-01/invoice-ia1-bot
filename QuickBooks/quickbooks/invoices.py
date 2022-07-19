"""Defines methods to interact with the QuickBooks Invoice object.

Functions
----------
*get_access_token_from_refresh_token
*revoke_token
*create_invoice
*get_invoice_pdf
"""

import requests
import logging
import yaml
from datetime import datetime

# Reading config file
with open('quickbooks/config.yaml', 'r') as stream:
    config = yaml.safe_load(stream)

BASE_URL = config['quickbooks_api']['base_url']
COMPANY_ID = str(config['quickbooks_api']['company_id'])
MINOR_VERSION = str(config['quickbooks_api']['minor_version'])


def get_access_token_from_refresh_token() -> str:
    """Gets the access token for use in other API calls.
    The access token is obtained using a refresh token.
    The new refresh token is saved in the config.yaml file.

        Parameters
        ----------
        n/a

        Returns
        -------
        Access token, if obtained; else, error message
    """
    discovery_doc = config['quickbooks_api']['authentication']['discovery_doc']
    client_id = config['quickbooks_api']['authentication']['client_id']
    client_secret = config['quickbooks_api']['authentication']['client_secret']
    refresh_token = config['quickbooks_api']['authentication']['refresh_token']

    # Getting token endpoint
    resp = requests.get(discovery_doc)
    token_endpoint = resp.json()['token_endpoint']

    # Getting access token (and new refresh token)
    headers = {'Accept': 'application/json'}
    payload = {'refresh_token': refresh_token,
               'grant_type': 'refresh_token'}
    logging.debug('Calling token endpoint...')
    resp = requests.post(token_endpoint,
                         data=payload,
                         headers=headers,
                         auth=(client_id, client_secret),
                         timeout=30)
    logging.debug('Response status: ' + str(resp.status_code))
    if resp.status_code != 200:
        logging.error("Error Desc.: \n" + resp.text)
        return 'Access token could not be obtained.'

    # Saving refresh token
    config['quickbooks_api']['authentication']['refresh_token'] = resp.json()[
        'refresh_token']
    with open('quickbooks/config.yaml', 'w') as file:
        file.write(yaml.safe_dump(config))

    return resp.json()['access_token']


def revoke_token(token: str) -> bool:
    """Revokes a token.

            Parameters
            ----------
            token:
                The token to revoke; could be access token or refresh token

            Returns
            -------
            True, if successful; else, False
    """
    discovery_doc = config['quickbooks_api']['authentication']['discovery_doc']
    client_id = config['quickbooks_api']['authentication']['client_id']
    client_secret = config['quickbooks_api']['authentication']['client_secret']

    # Getting revoke endpoint
    resp = requests.get(discovery_doc)
    revoke_endpoint = resp.json()['revocation_endpoint']

    # Revoking token
    headers = {'Accept': 'application/json',
               'content-type': 'application/json'}
    payload = {'token': token}
    logging.debug('Calling revoke endpoint...')
    resp = requests.post(revoke_endpoint,
                         json=payload,
                         headers=headers,
                         auth=(client_id, client_secret),
                         timeout=30)
    logging.debug("Response status: " + str(resp.status_code))
    logging.debug("Response body: " + "\n" + resp.text)

    return resp.status_code == 200


def _get_item_id(access_token, item_name):
    """Gets the item id associated with a product/service name."""

    headers = {'Authorization': 'Bearer ' + access_token,
               'Accept': 'application/json',
               'Content-Type': 'application/text'}
    request_body = "SELECT Id FROM item WHERE Name='" + item_name + "'"
    logging.debug('Calling endpoint to get item id for "'
                 + item_name + '"...')
    resp = requests.post(
        BASE_URL + '/v3/company/' + COMPANY_ID + '/query?minorversion=' +
        MINOR_VERSION,
        headers=headers,
        data=request_body,
        timeout=30)
    logging.debug('Response status: ' + str(resp.status_code))
    logging.debug('Response body: ' + '\n' + resp.text)

    if resp.status_code == 200:
        return resp.json()['QueryResponse']['Item'][0]['Id']
    else:
        resp.raise_for_status()


def _get_customer_refvalue(access_token, customer_name):
    """Gets the customer ref. number assc. with a customer display name."""

    headers = {"Authorization": "Bearer " + access_token,
               "Accept": "application/json",
               "Content-Type": "application/text"}
    request_body = "SELECT Id FROM Customer WHERE DisplayName='" + \
                   customer_name + "'"
    logging.debug("Calling endpoint to get customer reference id for '"
                 + customer_name + "'...")
    resp = requests.post(
        BASE_URL + "/v3/company/" + COMPANY_ID + "/query?minorversion=" +
        MINOR_VERSION,
        headers=headers,
        data=request_body,
        timeout=30)
    logging.debug("Response status: " + str(resp.status_code))
    logging.debug("Response body: " + "\n" + resp.text)

    if resp.status_code == 200:
        return resp.json()["QueryResponse"]["Customer"][0]["Id"]
    else:
        resp.raise_for_status()


def create_invoice(access_token: str, invoice_num: int, customer_name: str,
                   line_items: list, due_date: str, invoice_date: str =
                   None) -> int:
    """Creates an invoice in QuickBooks.

        Parameters
        ----------
        access_token:
            The bearer access token needed for authentication
        invoice_num:
            The invoice/document number to be used
        customer_name:
            A valid customer name; must match a Display Name in QuickBooks
        line_items:
            Products/services names and descriptions along with-
            1. flat rate [NOT SUPPORTED]; or
            2. hourly rate and number of hours; or
            3. quantity and price per unit
            Each *iterable* in the list needs to have the following details,
            and in the following order (in case of lists or tuples)-
            1. Total line amount (ONLY if flat-rate);
               if dict is passed, key="Amount"
            2. Product/service name; must match an item name in QuickBooks;
               if dict is passed, key="item_name"
            3. Product/service description;
               if dict is passed, key="item_desc"
            4. Quantity or number of hours (NOT Required if flat-rate);
               if dict is passed, key="qty"
            5. hourly rate or price per unit (NOT Required if flat-rate);
               if dict is passed, key="rate"
            NOTE: at least one line item needs to be provided
        due_date:
            The invoice due date in 'yyyy-mm-dd' format
        invoice_date:
            The invoice date in 'yyyy-mm-dd' format; if not provided,
            the date of run will be used

        Returns
        -------
        Invoice ID of the newly created invoice; if error, -1 is returned
    """
    # Checking if customer name is valid
    # If valid, getting the customer reference number
    try:
        customer_ref_id = _get_customer_refvalue(access_token, customer_name)
    except:
        logging.error("Customer Reference Id could not be determined.")
        return -1

    # Determining the line details
    if len(line_items) == 0:  # Checking if at least one line item exists
        logging.critical("No line items detected.")
        return -1
    line_details = []
    for line in line_items:
        if isinstance(line, dict):
            try:
                # Checking if item name is valid
                # If valid, getting the item Id
                item_id = _get_item_id(access_token, line["item_name"])
            except:
                logging.error("Customer Reference Id could not be determined.")
                return -1
            rate = float(str(line["rate"]).replace("$", "").replace(",", ""))
            amount = float(line["qty"]) * rate
            line_detail = {"DetailType": "SalesItemLineDetail",
                           "Amount": amount,
                           "SalesItemLineDetail": {
                               "ItemRef": {"value": item_id},
                               "Qty": float(line["qty"]),
                               "UnitPrice": rate
                           },
                           "Description": line["item_desc"]}
        elif isinstance(line, list) or isinstance(line, tuple):
            try:
                item_id = _get_item_id(access_token, line[0])
            except:
                logging.error("Customer Reference Id could not be determined.")
                return -1
            rate = float(str(line[3]).replace("$", "").replace(",", ""))
            amount = float(line[2]) * rate
            line_detail = {"DetailType": "SalesItemLineDetail",
                           "Amount": amount,
                           "SalesItemLineDetail": {
                               "ItemRef": {"value": item_id},
                               "Qty": float(line[2]),
                               "UnitPrice": rate
                           },
                           "Description": line[1]}
        else:
            logging.critical("Invalid iterable type in line_items.")
            return -1
        line_details.append(line_detail)
    logging.debug("Line details: \n" + line_details.__str__())

    # Determining invoice date
    if invoice_date is None:
        txn_date = datetime.now().strftime("%Y-%m-%d")
    else:
        txn_date = invoice_date

    # Creating invoice
    headers = {"Authorization": "Bearer " + access_token,
               "Accept": "application/json",
               "Content-Type": "application/json"}
    request_body = {"Line": line_details,
                    "CustomerRef": {"value": customer_ref_id},
                    "DueDate": due_date,
                    "DocNumber": str(invoice_num),
                    "TxnDate": txn_date}
    logging.debug("Calling endpoint to create invoice...")
    resp = requests.post(
        BASE_URL + "/v3/company/" + COMPANY_ID + "/invoice?minorversion=" +
        MINOR_VERSION,
        headers=headers,
        json=request_body,
        timeout=30)
    logging.debug("Response status: " + str(resp.status_code))
    logging.debug("Response body: " + "\n" + resp.text)

    if resp.status_code == 200:
        return int(resp.json()["Invoice"]["Id"])
    else:
        return -1


def get_invoice_pdf(access_token: str, invoice_id: int,
                    file_path: str) -> bool:
    """Saves an invoice as a pdf.

        Parameters
        ----------
        access_token:
            The bearer access token needed for authentication
        invoice_id:
            The invoice/document id of the invoice to be saved as pdf
        file_path:
            The file location and name to use for the pdf

        Returns
        -------
        True, if successful; else, False
    """
    # Getting invoice data
    headers = {"Authorization": "Bearer " + access_token}
    logging.debug("Calling endpoint to get invoice data for pdf...")
    resp = requests.get(
        BASE_URL + "/v3/company/" + COMPANY_ID + "/invoice/" + str(invoice_id)
        + "/pdf?minorversion=" + MINOR_VERSION,
        headers=headers,
        timeout=30)
    logging.info("Response status: " + str(resp.status_code))
    if resp.status_code != 200:
        logging.error("Error Desc.: \n" + resp.text)
        return False

    # Saving data as pdf
    logging.debug("Saving data as pdf.")
    try:
        with open(file_path, "wb") as file:
            file.write(resp.content)
        logging.info("Data saved.")
    except Exception as err:
        logging.error("Error Desc.: \n {0}".format(err))
        return False

    return True


if __name__ == '__main__':
    print('Please use this module for import only.')
