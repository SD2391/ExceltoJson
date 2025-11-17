# mapping_v1.py
import json

def run_mapping(input_json: dict):
    data = input_json
    final_data = {}

    def safe_get(path, default=None):
        try:
            part = data
            for p in path:
                part = part[p]
            return part
        except:
            return default

    final_data['BE TYPE']                = safe_get(["pages", 0, "tables", 0, "data", 0, "BE Type"])
    final_data['PORT CODE']              = safe_get(["pages", 0, "tables", 0, "data", 0, "Port Code"])
    final_data['BE No.']                 = safe_get(["pages", 0, "tables", 0, "data", 0, "BE No"])
    final_data['BE DATE']                = safe_get(["pages", 0, "tables", 0, "data", 0, "BE Da"])
    final_data['IEC']                    = safe_get(["pages", 0, "tables", 0, "data", 1, "BE No"])
    final_data['GSTIN']                  = safe_get(["pages", 0, "tables", 0, "data", 2, "BE No"])
    final_data['CB CODE']                = safe_get(["pages", 0, "tables", 0, "data", 3, "BE No"])
    final_data['CB NAME ']               = safe_get(["pages", 0, "tables", 0, "data", 13, "Column_19"])
    final_data['BE STATUS']              = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_3"])
    final_data['MODE']                   = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_5"])
    final_data['DEF BE']                 = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_7"])
    final_data['KACHA']                  = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_10"])
    final_data['SEC 48']                 = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_13"])
    final_data['REIMP']                  = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_15"])
    final_data['ADV BE']                 = safe_get(["pages", 0, "tables", 0, "data", 9, "Port Code"])
    final_data['ASSESS']                 = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_19"])
    final_data['EXAM']                   = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_22"])
    final_data['HSS']                    = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_27"])
    final_data['MAWB NO.']               = safe_get(["pages", 0, "tables", 0, "data", 24, "Port Code"])
    final_data['MAWB DATE']              = safe_get(["pages", 0, "tables", 0, "data", 24, "BE No"])
    final_data['FIRST CHECK']            = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_31"])
    final_data['PROV/FINAL']             = safe_get(["pages", 0, "tables", 0, "data", 9, "Column_35"])
    final_data['COUNTRY OF ORIGIN']      = safe_get(["pages", 0, "tables", 0, "data", 10, "Column_8"])
    final_data['COUNTRY OF CONSIGNMENT'] = safe_get(["pages", 0, "tables", 0, "data", 10, "BE Type"])
    final_data['PORT OF LOADING']        = safe_get(["pages", 0, "tables", 0, "data", 11, "Column_8"])
    final_data['PORT OF SHIPMENT']       = safe_get(["pages", 0, "tables", 0, "data", 11, "BE Type"])
    final_data['AD CODE']                = safe_get(["pages", 0, "tables", 0, "data", 18, "Column_6"])
    final_data['WBE No']                 = safe_get(["pages", 0, "tables", 0, "data", 33, "Column_3"])
    final_data['WBE DATE']               = safe_get(["pages", 0, "tables", 0, "data", 33, "Column_6"])
    final_data['OOC DATE']               = safe_get(["pages", 0, "tables", 0, "data", 38, "Column_6"])
    final_data['INVOICE NO.']            = safe_get(["pages", 0, "tables", 0, "data", 33, "Column_21"])
    final_data['INVOICE AMT']            = safe_get(["pages", 0, "tables", 0, "data", 33, "Column_31"])
    final_data['FREIGHT']                = safe_get(["pages", 1, "tables", 0, "data", 25, "Column_5"])
    final_data['INSURANCE']              = safe_get(["pages", 1, "tables", 0, "data", 25, "Column_6"])
    final_data['INVOICE DATE']           = safe_get(["pages", 1, "tables", 0, "data", 10, "Column_4"])
    final_data['CURRENCY']               = safe_get(["pages", 0, "tables", 0, "data", 33, "Column_36"])
    final_data['TERM']                   = safe_get(["pages", 1, "tables", 0, "data", 27, "Column_4"])
    final_data['PAY TERMS']              = safe_get(["pages", 1, "tables", 0, "data", 25, "Column_12"])
    final_data['BUYER NAME']             = safe_get(["pages", 1, "tables", 0, "data", 12, "Column_3"])
    final_data['BUYER ADDRESS']          = safe_get(["pages", 1, "tables", 0, "data", 13, "Column_3"])
    final_data['SELLER NAME']            = safe_get(["pages", 1, "tables", 0, "data", 12, "Port Code"])
    final_data['SELLER ADDRESS']         = safe_get(["pages", 1, "tables", 0, "data", 12, "Port Code"])
    final_data['SUPPLIER NAME']          = safe_get(["pages", 1, "tables", 0, "data", 18, "Column_3"])
    final_data['SUPPLIER ADDRESS']       = safe_get(["pages", 1, "tables", 0, "data", 20, "Column_3"])
    final_data['THIRD PARTY NAME']       = safe_get(["pages", 1, "tables", 0, "data", 17, "Port Code"])
    final_data['THIRD PARTY ADDRESS']    = safe_get(["pages", 1, "tables", 0, "data", 17, "Port Code"])
    final_data['CTH']                    = safe_get(["pages", 1, "tables", 0, "data", 32, "Column_4"])
    final_data['DESCRIPTION']            = safe_get(["pages", 1, "tables", 0, "data", 32, "Column_6"])
    final_data['QUANTITY']               = safe_get(["pages", 1, "tables", 0, "data", 32, "Column_15"])
    final_data['UQC']                    = safe_get(["pages", 1, "tables", 0, "data", 32, "BE Type"])
    final_data['VALUATION METHOD']       = safe_get(["pages", 1, "tables", 0, "data", 25, "Column_16"])
    final_data['CERTIFICATE NO.']        = safe_get(["pages", 3, "tables", 0, "data", 24, "Column_3"])
    final_data['CERTIFICATE DATE']       = safe_get(["pages", 3, "tables", 0, "data", 24, "Column_9"])

    return final_data
