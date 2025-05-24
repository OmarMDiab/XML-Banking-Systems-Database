from lxml import etree # Keep for parsing results if needed
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import operator
import uuid
import os
from pathlib import Path
import json

# import date
from datetime import datetime
from BaseXClient import Session
import uuid
import xml.etree.ElementTree as ET # Using standard library for simple parsing
import pandas as pd # For DataFrame operations if needed
import re

class BankingXMLQueries:
    def __init__(self, db_name: str = 'banking', db_host: str = 'localhost', db_port: int = 1984, db_user: str = 'Bank_Admin', db_pass: str = 'bankadmin'):
        """Initialize with BaseX connection details"""
        self.main_dir = "Banking_System/"
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_name = db_name
        self.cards_xsd_path = os.path.join(self.main_dir, 'cards.xsd') 
        self.users_xsd_path = os.path.join(self.main_dir, 'users.xsd') 
        self.accounts_xsd_path = os.path.join(self.main_dir, 'accounts.xsd') 
        self.transactions_xsd_path = os.path.join(self.main_dir, 'transactions.xsd') 
        self.loans_xsd_path = os.path.join(self.main_dir, 'loans.xsd') 
        self.employees_xsd_path = os.path.join(self.main_dir, 'employees.xsd')

   
    def _execute_query(self, query: str) -> str:
        """Helper to execute an XQuery against BaseX"""
        session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
        try:
            session.execute(f"OPEN {self.db_name}")
            result = session.execute(f'XQUERY {query}')
            return result
        except IOError as e:
            # Handle potential connection errors more gracefully
            print(f"BaseX connection error: {e}")
            raise ConnectionError(f"Could not connect to BaseX server at {self.db_host}:{self.db_port}") from e
        finally:
            session.close()

    def _parse_xml_string(self, xml_string: str, root_tag: str, item_tag: str) -> List[Dict]:
        """Parses an XML string potentially containing multiple items."""
        if not xml_string or not xml_string.strip():
            return []
        try:
            # Wrap the result if it doesn't have a single root element
            if not xml_string.strip().startswith('<'):
                 # Handle cases where BaseX might return non-XML (e.g., simple values, errors)
                 # This basic parser expects XML. Adjust if queries return other types.
                 print(f"Warning: Received non-XML string: {xml_string}")
                 return []

            # Ensure a single root element for parsing
            # If the result is a sequence of elements, wrap them
            if xml_string.count('<' + item_tag + '>') > 1 and not xml_string.strip().startswith(f'<{root_tag}>'):
                 full_xml = f"<{root_tag}>{xml_string}</{root_tag}>"
            elif not xml_string.strip().startswith(f'<{root_tag}>') and xml_string.strip().startswith(f'<{item_tag}>'):
                 # Handle case of a single item returned without the root
                 full_xml = f"<{root_tag}>{xml_string}</{root_tag}>"
            else:
                 full_xml = xml_string

            root = ET.fromstring(full_xml) # Use standard library XML parser
            return [self._element_to_dict(elem) for elem in root.findall(item_tag)]
        except ET.ParseError as e:
            print(f"Error parsing XML string: {e}\nXML String: {xml_string[:500]}...") # Log snippet
            return [] # Return empty list on parsing error
        except Exception as e: # Catch other potential errors
            print(f"Unexpected error during XML parsing: {e}")
            return []

    def _parse_single_xml_item(self, xml_string: str) -> Optional[Dict]:
         """ Parses an XML string expected to contain a single item."""
         if not xml_string or not xml_string.strip():
             return None
         try:
             # Check if it's valid XML before parsing
             if not xml_string.strip().startswith('<'):
                 print(f"Warning: Expected single XML item, got non-XML: {xml_string}")
                 return None
             root = ET.fromstring(xml_string)
             return self._element_to_dict(root)
         except ET.ParseError as e:
             print(f"Error parsing single XML item: {e}\nXML String: {xml_string[:500]}...")
             return None
         except Exception as e:
            print(f"Unexpected error during single XML item parsing: {e}")
            return None
    
    def _validate_xml_against_xsd(self, xml_str: str, xsd_path: str) -> tuple[bool, str]:
        """Validates an XML string against an XSD schema. Returns (bool, error_message_or_empty_string)."""
        try:
            xml_doc = etree.fromstring(xml_str.encode('utf-8')) # Ensure UTF-8 encoding
            with open(xsd_path, 'rb') as f:
                xsd_doc_content = f.read()
            if not xsd_doc_content:
                return False, f"XSD file is empty: {xsd_path}"
            xsd_doc = etree.XML(xsd_doc_content)
            schema = etree.XMLSchema(xsd_doc)
            is_valid = schema.validate(xml_doc)
            if not is_valid:
                error_log = schema.error_log
                # Limit the number of errors displayed for brevity
                errors = [f"{e.message} (line {e.line}, column {e.column})" for e in error_log][:5]
                return False, f"XSD Validation Errors: {'; '.join(errors)}"
            return True, ""
        except etree.XMLSchemaParseError as e:
            return False, f"XSD Schema Parse Error: {e} (XSD: {xsd_path})"
        except etree.XMLSyntaxError as e:
            # Include a snippet of the XML that failed to parse
            return False, f"XML Syntax Error during validation: {e}. XML Snippet: {xml_str[:250]}..."
        except FileNotFoundError:
            return False, f"XSD file not found: {xsd_path}"
        except Exception as e:
            return False, f"Generic XSD Validation Error: {e}"
        
    def validate_user_data(self, user_data: Dict) -> Optional[str]:
        required = ['FullName', 'Email', 'Phone', 'Address', 'Role', 'Username', 'PasswordHash']
        missing = [f for f in required if f not in user_data]
        if missing:
            return f"Error: Missing required user fields: {', '.join(missing)}"

        address = user_data.get('Address')
        if not isinstance(address, dict) or not all(k in address for k in ['Country', 'City', 'Street']):
            return "Error: Missing or incomplete Address fields (Country, City, Street required)"
        
        # Validate address fields
        for k in ['Country', 'City']:
            val = address.get(k)
            if not isinstance(val, str) or not val.strip():
                return f"Error: {k} must be a non-empty string"
            # Country and City should only contain letters and spaces
            if not re.match(r"^[A-Za-z\s]+$", val.strip()):
                return f"Error: {k} must only contain letters and spaces"

        # Street can contain digits and letters
        street = address.get('Street')
        if not isinstance(street, str) or not street.strip():
            return "Error: Street must be a non-empty string"
        if street.strip().isdigit():
            return "Error: Street cannot contain only digits"
        
        # Full name validation
        full_name = user_data['FullName']
        if not isinstance(full_name, str) or not full_name.strip() or full_name.isdigit():
            return "Error: FullName must be a non-empty string and not only digits"

        # Email validation
        email = user_data['Email']
        if not isinstance(email, str) or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return "Error: Invalid email format"

        # Phone validation
        phone = user_data['Phone']
        if not isinstance(phone, str):
            phone = str(phone)
        if not re.match(r"^\+?\d{7,15}$", phone):
            return "Error: Invalid phone number format"

        # Role validation
        role = user_data['Role']
        if role not in ['customer', 'employee']:
            return "Error: Role must be 'customer' or 'employee'"

        # Username and Password validation
        username = user_data['Username']
        password_hash = user_data['PasswordHash']
        if not isinstance(username, str) or not username.strip():
            return "Error: Username must be a non-empty string"
        if not isinstance(password_hash, str) or not password_hash.strip():
            return "Error: PasswordHash must be a non-empty string"

        return None  # No errors


    # ==============================================
    # CRUD Operations - Users (Keep existing XQuery implementations)
    # ==============================================

    def create_user(self, user_data: Dict) -> str:
        # Validate user data
        validation_error = self.validate_user_data(user_data)
        if validation_error:
            return validation_error
        
        user_id = user_data.get("UserID", f"USER-{uuid.uuid4().hex[:8].upper()}")
        full_name = user_data["FullName"]
        email = user_data["Email"]
        phone = user_data["Phone"]
        address_data = user_data["Address"]
        country = address_data["Country"]
        city = address_data["City"]
        street = address_data["Street"]
        role = user_data["Role"]
        username = user_data["Username"]
        password_hash = user_data["PasswordHash"]

        user_xml = f'''
            <User>
                <UserID>{user_id}</UserID>
                <FullName>{full_name}</FullName>
                <Email>{email}</Email>
                <Phone>{phone}</Phone>
                <Address>
                    <Country>{country}</Country>
                    <City>{city}</City>
                    <Street>{street}</Street>
                </Address>
                <Role>{role}</Role>
                <Username>{username}</Username>
                <PasswordHash>{password_hash}</PasswordHash>
            </User>
        '''.strip()

        user_xml_for_validation = f'<Users>{user_xml}</Users>'

        is_valid, validation_error_msg = self._validate_xml_against_xsd(user_xml_for_validation, self.users_xsd_path)
        if not is_valid:
            return f"Validation failed: User data does not conform to XSD. Details: {validation_error_msg}"

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Check for existing UserID
            user_id_query = f'XQUERY exists(doc("{self.db_name}/users.xml")//User[UserID="{user_id}"])'
            if session.execute(user_id_query).strip() == "true":
                return f"Cannot create user: User ID {user_id} already exists"

            # Check for existing Email
            email_query = f'XQUERY exists(doc("{self.db_name}/users.xml")//User[Email="{email}"])'
            if session.execute(email_query).strip() == "true":
                return f"Cannot create user: Email {email} already exists"

            # Check for existing Username
            username_query = f'XQUERY exists(doc("{self.db_name}/users.xml")//User[Username="{username}"])'
            if session.execute(username_query).strip() == "true":
                return f"Cannot create user: Username {username} already exists"

            # Insert new user
            insert_node = etree.tostring(etree.fromstring(user_xml)).decode()
            insert_query = f'''
            XQUERY insert node {insert_node}
            into doc("{self.db_name}/users.xml")/Users
            '''
            session.execute(insert_query)
            return f"User {user_id} created successfully."

        except Exception as e:
            print(f"Error creating user: {e}")
            return f"An error occurred during user creation: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()

    def update_user(self, user_id: str, update_data: Dict) -> str:
        # Validate user data
        validation_error = self.validate_user_data(update_data)
        if validation_error:
            return validation_error



        new_email = update_data.get("Email")
        new_fullname = update_data.get("FullName")
        new_phone = update_data.get("Phone")
        addr = update_data.get("Address", {})
        new_country = addr.get("Country")
        new_city = addr.get("City")
        new_street = addr.get("Street")
        new_role = update_data.get("Role")
        new_username = update_data.get("Username") # Assuming username cannot be updated or if it can, needs uniqueness check.
                                                 # For this example, we'll assume it's part of the full replacement.
        new_password_hash = update_data.get("PasswordHash")

       
        # Construct the new User XML node based on input
        # This node should also be validated against users.xsd if it's significantly different from creation
        updated_user_xml_node = f'''
        <User>
            <UserID>{user_id}</UserID>
            <FullName>{new_fullname}</FullName>
            <Email>{new_email}</Email>
            <Phone>{new_phone}</Phone>
            <Address>
                <Country>{new_country}</Country>
                <City>{new_city}</City>
                <Street>{new_street}</Street>
            </Address>
            <Role>{new_role}</Role>
            <Username>{new_username}</Username>
            <PasswordHash>{new_password_hash}</PasswordHash>
        </User>
        '''.strip()

        validation_updated_user_xml_node   = f'<Users>{updated_user_xml_node}</Users>'
        # Optional: Validate the constructed updated_user_xml_node against users_xsd_path
        is_valid, validation_error_msg = self._validate_xml_against_xsd(validation_updated_user_xml_node, self.users_xsd_path)
        if not is_valid:
            return f"Validation failed: Updated user data does not conform to XSD. Details: {validation_error_msg}"

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if the user to update exists
            user_exists_query = f'XQUERY exists(doc("{self.db_name}/users.xml")//User[UserID="{user_id}"])'
            if session.execute(user_exists_query).strip() != "true":
                return f"User with ID {user_id} not found."

            # Step 2: Check if the new email already exists for another user
            if new_email: # Only check if email is being changed/provided
                email_conflict_query = f'''
                XQUERY exists(doc("{self.db_name}/users.xml")//User[Email="{new_email}" and UserID!="{user_id}"])
                '''
                if session.execute(email_conflict_query).strip() == "true":
                    return f"Email '{new_email}' already exists for another user. Please choose a different email."

            # Step 3: Check if the new username already exists for another user (if username can be updated)
            if new_username: 
                username_conflict_query = f'''
                XQUERY exists(doc("{self.db_name}/users.xml")//User[Username="{new_username}" and UserID!="{user_id}"])
                '''
                if session.execute(username_conflict_query).strip() == "true":
                    return f"Username '{new_username}' already exists for another user. Please choose a different username."


            # Step 4: Replace the user node
            replace_query = f'''
            XQUERY replace node doc("{self.db_name}/users.xml")//User[UserID="{user_id}"]
            with {updated_user_xml_node}
            '''
            session.execute(replace_query)
            return "User updated successfully."

        except Exception as e:
            print(f"Error updating user {user_id}: {e} (Type: {type(e).__name__})")
            return f"An error occurred during user update: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()

    # ==============================================
    # CRUD Operations - Accounts (Keep existing XQuery implementations)
    # ==============================================


    def validate_account_data(self, account_data: Dict) -> Optional[str]:
        required = ['UserID', 'AccountType', 'Balance', 'Currency']
        missing = [f for f in required if f not in account_data]
        if missing:
            return f"Error: Missing required account fields: {', '.join(missing)}"

        # Validate UserID
        if not isinstance(account_data['UserID'], str) or not account_data['UserID'].strip():
            return "Error: UserID must be a non-empty string."

        # Validate AccountType
        if not isinstance(account_data['AccountType'], str) or account_data['AccountType'].lower() not in ['checking', 'savings', 'business']:
            return "Error: AccountType must be one of ['checking', 'savings', 'business']."

        # Validate Balance
        try:
            Decimal(account_data['Balance'])
        except Exception:
            return "Error: Invalid Balance format. Expected a numeric value."

        # Validate Currency (optional: limit to ISO codes)
        if not isinstance(account_data['Currency'], str) or len(account_data['Currency']) != 3:
            return "Error: Currency must be a 3-letter ISO code string (e.g., 'USD')."

        # Validate OpenDate if present
        open_date = account_data.get('OpenDate')
        if open_date:
            try:
                datetime.strptime(open_date.split('T')[0], '%Y-%m-%d')
            except Exception:
                return "Error: Invalid OpenDate format. Expected YYYY-MM-DD."

       

        return None  # All checks passed
 
    def create_account(self, account_data: Dict) -> str:
        # Validate account data
        validation_error = self.validate_account_data(account_data)
        if validation_error:
            return validation_error
        
        account_id = account_data.get('AccountID', f"ACC-{uuid.uuid4().hex[:8].upper()}")
        user_id = account_data['UserID']
        account_type = account_data['AccountType']
        try:
            balance = str(Decimal(account_data['Balance']))
        except Exception:
            return "Error: Invalid Balance format. Expected a number."
        currency = account_data['Currency']
        status = account_data.get('Status', 'active')
        try:
            open_date_obj = datetime.strptime(account_data.get('OpenDate', datetime.now().strftime('%Y-%m-%d')).split('T')[0], '%Y-%m-%d')
            open_date = open_date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return "Error: Invalid OpenDate format. Expected YYYY-MM-DD."

        # XML for the single account entity
        single_account_xml = f'''
        <Account>
            <AccountID>{account_id}</AccountID>
            <UserID>{user_id}</UserID>
            <AccountType>{account_type}</AccountType>
            <Balance>{balance}</Balance>
            <Currency>{currency}</Currency>
            <Status>{status}</Status>
            <OpenDate>{open_date}</OpenDate>
        </Account>
        '''.strip()

        validation_account_xml = f'<Accounts>{single_account_xml}</Accounts>'
        # Validate the single account XML
        # Assuming accounts_xsd_path defines <Account>
        is_valid, validation_error_msg = self._validate_xml_against_xsd(validation_account_xml, self.accounts_xsd_path)
        if not is_valid:
            return f"Validation failed: Account data does not conform to XSD. Details: {validation_error_msg}"

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if UserID exists
            user_exists_query = f'XQUERY exists(doc("{self.db_name}/users.xml")//User[UserID="{user_id}"])'
            if session.execute(user_exists_query).strip() != "true":
                return f"Cannot create account: User {user_id} not found."

            # Step 2: Check if AccountID already exists
            account_id_exists_query = f'XQUERY exists(doc("{self.db_name}/accounts.xml")//Account[AccountID="{account_id}"])'
            if session.execute(account_id_exists_query).strip() == "true":
                return f"Cannot create account: Account ID {account_id} already exists."

            # Step 3: Insert new account
            insert_query = f'''
            XQUERY insert node {single_account_xml}
            into doc("{self.db_name}/accounts.xml")/Accounts
            '''
            session.execute(insert_query)
            return f"Account {account_id} created successfully."

        except Exception as e:
            print(f"Error creating account: {e} (Type: {type(e).__name__})")
            return f"An error occurred during account creation: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()


    def update_account_balance(self, account_id: str, amount: Decimal) -> str:
        try:
            amount_str = str(Decimal(amount)) # Validate and format
        except Exception:
            return "Error: Invalid amount format. Expected a number."

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if the account exists
            account_exists_query = f'XQUERY exists(doc("{self.db_name}/accounts.xml")//Account[AccountID="{account_id}"])'
            if session.execute(account_exists_query).strip() != "true":
                return f"Account with ID {account_id} does not exist."

            # Step 2: Update the balance
            update_balance_query = f'''
            XQUERY replace value of node doc("{self.db_name}/accounts.xml")//Account[AccountID="{account_id}"]/Balance
            with xs:decimal("{amount_str}")
            '''
            session.execute(update_balance_query)
            # BaseX 'replace value of node' typically returns empty on success.
            return f"Balance for account {account_id} updated successfully to {amount_str}."

        except Exception as e:
            print(f"Error updating balance for account {account_id}: {e} (Type: {type(e).__name__})")
            return f"An error occurred during balance update: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()

    def close_account(self, account_id: str) -> str:
        check_query = f'''
        declare variable $accountID as xs:string := "{account_id}";
        let $statusNode := doc("{self.db_name}/accounts.xml")/Accounts/Account[AccountID = $accountID]/Status
        return exists($statusNode)
        '''

        update_query = f'''
        declare variable $accountID as xs:string := "{account_id}";
        replace value of node 
            doc("{self.db_name}/accounts.xml")/Accounts/Account[AccountID = $accountID]/Status 
        with "closed"
        '''

        session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
        try:
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if account exists
            exists_result = session.execute(f'XQUERY {check_query}')
            if exists_result.strip() == 'true':
                # Step 2: Perform update
                session.execute(f'XQUERY {update_query}')
                return f"Account {account_id} has been successfully closed."
            else:
                return f"Account with ID {account_id} does not exist."
        except Exception as e:
            print(f"Error closing account {account_id}: {e}")
            return f"An error occurred while closing the account: {e}"
        finally:
            session.close()


    # ==============================================
    # CRUD Operations - Transactions (Keep existing XQuery implementations)
    # ==============================================
    def validate_transaction_data(self, transaction_data: Dict) -> Optional[str]:
        required = ['FromAccountID', 'ToAccountID', 'Amount', 'Type']
        missing = [f for f in required if f not in transaction_data]
        if missing:
            return f"Error: Missing required transaction fields: {', '.join(missing)}"

        # Validate FromAccountID and ToAccountID
        if not all(isinstance(transaction_data[key], str) and transaction_data[key].strip()
                for key in ['FromAccountID', 'ToAccountID']):
            return "Error: FromAccountID and ToAccountID must be non-empty strings."

        # Validate Amount
        try:
            Decimal(transaction_data['Amount'])
        except Exception:
            return "Error: Invalid Amount format. Expected a numeric value."

        # Validate Timestamp (optional)
        timestamp_str = transaction_data.get('Timestamp')
        if timestamp_str:
            try:
                datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception:
                return "Error: Invalid Timestamp format. Expected ISO 8601 format."

        return None  # All validations passed




    def create_transaction(self, transaction_data: Dict) -> str:
    #    validate transaction data
        validation_error = self.validate_transaction_data(transaction_data)
        if validation_error:
            return validation_error
        # validate that from and to account are not the same
        if transaction_data['FromAccountID'] == transaction_data['ToAccountID']:
            return "Error: FromAccountID and ToAccountID cannot be the same."
        

        transaction_id = transaction_data.get('TransactionID', f"TX-{uuid.uuid4().hex[:8].upper()}")
        from_acc = transaction_data['FromAccountID']
        to_acc = transaction_data['ToAccountID']
        try:
            amount = str(Decimal(transaction_data['Amount']))
            # round the decimal to 2 decimal places
            amount = str(Decimal(amount).quantize(Decimal('0.01')))  # Round to 2 decimal places
        except Exception:
            return "Error: Invalid Amount format. Expected a number."
      
        tx_type = transaction_data['Type']
        status = transaction_data.get('Status', 'completed')

        try:
            timestamp_str = transaction_data.get('Timestamp', datetime.now().isoformat())
            # Parse and validate ISO format, then strip microseconds
            parsed_datetime = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            timestamp = parsed_datetime.strftime("%Y-%m-%dT%H:%M:%S")  # Format without microseconds
        except ValueError:
            return "Error: Invalid Timestamp format. Expected ISO 8601 format."

        transaction_xml = f'''
            <Transaction>
                <TransactionID>{transaction_id}</TransactionID>
                <FromAccountID>{from_acc}</FromAccountID>
                <ToAccountID>{to_acc}</ToAccountID>
                <Amount>{amount}</Amount>
                <Date>{timestamp}</Date>
                <Type>{tx_type}</Type>
                <Status>{status}</Status>
            </Transaction>
        '''.strip()

        transaction_xml_for_validation = f'<Transactions>{transaction_xml}</Transactions>'

        is_valid, validation_error_msg = self._validate_xml_against_xsd(
            transaction_xml_for_validation, self.transactions_xsd_path)
        if not is_valid:
            return f"Validation failed: Transaction data does not conform to XSD. Details: {validation_error_msg}"

        session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
        try:
            session.execute(f"OPEN {self.db_name}")

            # Query 1: Check if the transaction ID already exists
            check_tx_id_query = f'XQUERY exists(doc("{self.db_name}/transactions.xml")//Transaction[TransactionID="{transaction_id}"])'
            if session.execute(check_tx_id_query).strip() == "true":
                return f"Cannot create transaction: Transaction ID {transaction_id} already exists"

            # Query 2: Check if the 'FromAccountID' exists
            check_from_acc_query = f'XQUERY exists(doc("{self.db_name}/accounts.xml")//Account[AccountID="{from_acc}"])'
            if session.execute(check_from_acc_query).strip() != "true":
                return f"Cannot create transaction: FromAccountID {from_acc} not found"

            # Query 3: Check if the 'ToAccountID' exists
            check_to_acc_query = f'XQUERY exists(doc("{self.db_name}/accounts.xml")//Account[AccountID="{to_acc}"])'
            if session.execute(check_to_acc_query).strip() != "true":
                return f"Cannot create transaction: ToAccountID {to_acc} not found"

            # Query 4: Insert the new transaction
            insert_query = f'''
                XQUERY insert node {etree.tostring(etree.fromstring(transaction_xml)).decode()}
                into doc("{self.db_name}/transactions.xml")/Transactions
            '''
            session.execute(insert_query)
            return f"Transaction {transaction_id} created successfully."

        except Exception as e:
            print(f"Error creating transaction: {e}")
            return f"An error occurred during transaction creation: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()



    def update_transaction_status(self, transaction_id: str, new_status: str) -> str:
        if not new_status: # Basic validation for new_status
            return "Error: New status cannot be empty."
        # Consider adding validation for allowed status values based on your XSD or business logic.

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if the transaction exists
            transaction_exists_query = f'XQUERY exists(doc("{self.db_name}/transactions.xml")//Transaction[TransactionID="{transaction_id}"])'
            if session.execute(transaction_exists_query).strip() != "true":
                return f"Transaction with ID {transaction_id} does not exist."

            # Step 2: Update the status
            update_status_query = f'''
            XQUERY replace value of node doc("{self.db_name}/transactions.xml")//Transaction[TransactionID="{transaction_id}"]/Status
            with "{new_status}"
            '''
            session.execute(update_status_query)
            return f"Transaction {transaction_id} status updated to {new_status}."

        except Exception as e:
            print(f"Error updating transaction {transaction_id}: {e} (Type: {type(e).__name__})")
            return f"An error occurred during transaction status update: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()

    # ==============================================
    # CRUD Operations - Loans (Keep existing XQuery implementations)
    # ==============================================
    def create_loan(self, loan_data: Dict) -> str:
        required_fields = ['UserID', 'LoanAmount', 'InterestRate', 'Duration']
        missing_fields = [f for f in required_fields if f not in loan_data]
        if missing_fields:
            return f"Error: Missing required loan fields: {', '.join(missing_fields)}"
       
        loan_id = loan_data.get('LoanID', f"LOAN-{uuid.uuid4().hex[:8].upper()}")
        user_id = loan_data['UserID']

        

        try:
            amount = str(Decimal(loan_data['LoanAmount']))
            # round the decimal to 2 decimal places
            amount = str(Decimal(amount).quantize(Decimal('0.01')))  # Round to 2 decimal places
            interest_rate = str(Decimal(loan_data['InterestRate']).quantize(Decimal('0.01')))  # Round to 2 decimal places
            # interest rate cant be zero or negative
            if float(interest_rate) <= 0:
                return "Error: InterestRate must be a positive number."
        except Exception:
            return "Error: Invalid Amount or InterestRate format. Expected a number."

        duration = str(loan_data['Duration'])
        status = loan_data.get('Status', 'requested')

        try:
            raw_date = loan_data.get('StartDate', datetime.now().strftime('%Y-%m-%d'))
            start_date = datetime.strptime(raw_date.split('T')[0], '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return "Error: Invalid StartDate format. Expected YYYY-MM-DD."

        # XML for the single loan entity wrapped with <Loans> root for validation


        single_loan_xml = f'''
        <Loan>
            <LoanID>{loan_id}</LoanID>
            <UserID>{user_id}</UserID>
            <LoanAmount>{amount}</LoanAmount>
            <InterestRate>{interest_rate}</InterestRate>
            <StartDate>{start_date}</StartDate>
            <Duration>{duration}</Duration>
            <Status>{status}</Status>
        </Loan>
        '''.strip()

        # wrap loans by loans
        validation_loan_xml = f'<Loans>{single_loan_xml}</Loans>'
        # Validate the single loan XML
        # Assuming loans_xsd_path defines <Loan>
        is_valid, validation_error_msg = self._validate_xml_against_xsd(validation_loan_xml, self.loans_xsd_path)
        if not is_valid:
            return f"Validation failed: Loan data does not conform to XSD. Details: {validation_error_msg}"

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if UserID exists
            user_exists_query = f'XQUERY exists(doc("{self.db_name}/users.xml")//User[UserID="{user_id}"])'
            if session.execute(user_exists_query).strip() != "true":
                return f"Cannot create loan: User {user_id} not found."

            # Step 2: Check if LoanID already exists
            loan_id_exists_query = f'XQUERY exists(doc("{self.db_name}/loans.xml")//Loan[LoanID="{loan_id}"])'
            if session.execute(loan_id_exists_query).strip() == "true":
                return f"Cannot create loan: Loan ID {loan_id} already exists."

            # Step 3: Insert new loan
            insert_query = f'''
            XQUERY insert node {single_loan_xml}
            into doc("{self.db_name}/loans.xml")/Loans
            '''
            session.execute(insert_query)
            return f"Loan {loan_id} created successfully."

        except Exception as e:
            print(f"Error creating loan: {e} (Type: {type(e).__name__})")
            return f"An error occurred during loan creation: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()



    def approve_loan(self, loan_id: str) -> str:
        new_status = "approved" # Fixed status for this method

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if the loan exists
            loan_exists_query = f'XQUERY exists(doc("{self.db_name}/loans.xml")//Loan[LoanID="{loan_id}"])'
            if session.execute(loan_exists_query).strip() != "true":
                return f"Loan with ID {loan_id} does not exist."

            # Step 2: Update the status to APPROVED
            approve_loan_query = f'''
            XQUERY replace value of node doc("{self.db_name}/loans.xml")//Loan[LoanID="{loan_id}"]/Status
            with "{new_status}"
            '''
            session.execute(approve_loan_query)
            return f"Loan {loan_id} has been successfully approved."

        except Exception as e:
            print(f"Error approving loan {loan_id}: {e} (Type: {type(e).__name__})")
            return f"An error occurred during loan approval: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()


    # ==============================================
    # CRUD Operations - Cards (Keep existing XQuery implementations)
    # ==============================================

    def validate_card_data(self, card_data: Dict) -> Optional[str]:
            required = ['AccountID', 'CardType', 'CardNumber', 'CVV', 'ExpiryDate']
            missing_fields = [field for field in required if field not in card_data]
            if missing_fields:
                return f"Error: Missing required card fields: {', '.join(missing_fields)}"

            # Validate CVV is numeric and 3–4 digits
            if not str(card_data['CVV']).isdigit() or not (3 <= len(str(card_data['CVV'])) <= 4):
                return "Error: Invalid CVV. Must be a 3 or 4-digit number."

        # Validate CardNumber format (allow dashes but ensure 12–19 digits total)
            raw_card_number = str(card_data['CardNumber']).replace('-', '')

            if not raw_card_number.isdigit() or not (12 <= len(raw_card_number) <= 19):
                return "Error: Invalid CardNumber. Must be 12–19 digits, optionally separated by dashes ('-')."

            # Validate expiry date format
            try:
                datetime.strptime(str(card_data['ExpiryDate']).split('T')[0], '%Y-%m-%d')
            except ValueError:
                return "Error: Invalid ExpiryDate format. Expected YYYY-MM-DD."

        
            valid_statuses = ['active', 'inactive', 'blocked', 'expired']
            if 'Status' in card_data and card_data['Status'].lower() not in valid_statuses:
                return f"Error: Status must be one of {valid_statuses}."

            return None

    def create_card(self, card_data: Dict) -> str:
        # Validate card data
        validation_error = self.validate_card_data(card_data)
        if validation_error:
            return validation_error

        card_id = card_data.get('CardID', f"CARD-{uuid.uuid4().hex[:8].upper()}")
        account_id = card_data['AccountID']
        card_type = card_data['CardType']
        card_number = card_data['CardNumber']
        cvv = card_data['CVV']
        try:
            expiry_date_obj = datetime.strptime(str(card_data['ExpiryDate']).split('T')[0], '%Y-%m-%d')
            expiry_date = expiry_date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return "Error: Invalid ExpiryDate format. Expected YYYY-MM-DD."
        status = card_data.get('Status', 'active')

        # XML for the single card entity wrapped with <Cards> root


        single_card_xml = f'''
            <Card>
                <CardID>{card_id}</CardID>
                <AccountID>{account_id}</AccountID>
                <CardType>{card_type}</CardType>
                <CardNumber>{card_number}</CardNumber>
                <CVV>{cvv}</CVV>
                <ExpiryDate>{expiry_date}</ExpiryDate>
                <Status>{status}</Status>
            </Card>
        '''.strip()

        validation_card_xml = f'<Cards>{single_card_xml}</Cards>'
        # Validate the single card XML against its XSD
        # Assuming cards_xsd_path defines the <Card> element
        is_valid, validation_error_msg = self._validate_xml_against_xsd(validation_card_xml, self.cards_xsd_path)
        if not is_valid:
            return f"Validation failed: Card data does not conform to XSD. Details: {validation_error_msg}"

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if AccountID exists
            account_exists_query = f'XQUERY exists(doc("{self.db_name}/accounts.xml")//Account[AccountID="{account_id}"])'
            if session.execute(account_exists_query).strip() != "true":
                return f"Cannot create card: Account {account_id} not found."

            # Step 2: Check if CardNumber already exists
            card_number_exists_query = f'XQUERY exists(doc("{self.db_name}/cards.xml")//Card[CardNumber="{card_number}"])'
            if session.execute(card_number_exists_query).strip() == "true":
                return f"Cannot create card: Card number {card_number} already exists."

            # Step 3: Check if CardID already exists
            card_id_exists_query = f'XQUERY exists(doc("{self.db_name}/cards.xml")//Card[CardID="{card_id}"])'
            if session.execute(card_id_exists_query).strip() == "true":
                return f"Cannot create card: Card ID {card_id} already exists."

            # Step 4: Insert new card
            insert_query = f'''
            XQUERY insert node {single_card_xml}
            into doc("{self.db_name}/cards.xml")/Cards
            '''
            session.execute(insert_query)
            return f"Card {card_id} created successfully."

        except Exception as e:
            print(f"Error creating card: {e} (Type: {type(e).__name__})")
            return f"An error occurred during card creation: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()

    def block_card(self, card_id: str) -> bool:
        """Cancel a card by setting its status to blocked using XQuery"""
        
        check_existence_query = f'''
        declare variable $cardID as xs:string := "{card_id}";
        if (exists(doc("{self.db_name}/cards.xml")//Card[CardID=$cardID])) then "exists"
        else "not found"
        '''
        
        update_card_query = f'''
        declare variable $cardID as xs:string := "{card_id}";
        replace value of node doc("{self.db_name}/cards.xml")//Card[CardID=$cardID]/Status with "blocked"
        '''

        session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
        try:
            session.execute(f"OPEN {self.db_name}")
            result = session.execute(f'XQUERY {check_existence_query}').strip()
            if result == "exists":
                session.execute(f'XQUERY {update_card_query}')
                return True
            elif result == "not found":
                print(f"Card cancellation failed: Card {card_id} not found.")
                return False
            else:
                print(f"Unexpected result from card check: {result}")
                return False
        except Exception as e:
            print(f"Error cancelling card {card_id}: {e}")
            return False
        finally:
            session.close()




    # ==============================================
    # CRUD Operations - Employees (Keep existing XQuery implementations)
    # ==============================================
    def create_employee(self, employee_data: Dict) -> str:
        required = ['UserID', 'Position', 'BranchID', 'Salary']
        missing = [f for f in required if f not in employee_data]
        if missing:
            return f"Error: Missing required employee fields: {', '.join(missing)}"
        # validate that position is a string
        if not isinstance(employee_data['Position'], str) or not employee_data['Position'].strip():
            return "Error: Invalid Position format. Expected a non-empty string."

        user_id = employee_data['UserID']
        position = employee_data['Position']
        branch_id = employee_data['BranchID']
        try:
            salary = str(Decimal(employee_data['Salary']))
            # round the decimal to 2 decimal places
            salary = str(Decimal(salary).quantize(Decimal('0.01')))  # Round to 2 decimal places
        except Exception:
            return "Error: Invalid Salary format. Expected a number."
        employee_id = employee_data.get('EmployeeID', f"EMP-{uuid.uuid4().hex[:8].upper()}")
        try:
            hire_date_obj = datetime.strptime(employee_data.get('HireDate', datetime.now().strftime('%Y-%m-%d')).split('T')[0], '%Y-%m-%d')
            hire_date = hire_date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return "Error: Invalid HireDate format. Expected YYYY-MM-DD."

        # XML for the single employee entity
        single_employee_xml = f'''
        <Employee>
            <EmployeeID>{employee_id}</EmployeeID>
            <UserID>{user_id}</UserID>
            <Position>{position}</Position>
            <BranchID>{branch_id}</BranchID>
            <HireDate>{hire_date}</HireDate>
            <Salary>{salary}</Salary>
        </Employee>
        '''.strip()

        validation_employee_xml = f'<Employees>{single_employee_xml}</Employees>'
        # Validate the single employee XML
        # Assuming employees_xsd_path defines <Employee>
        is_valid, validation_error_msg = self._validate_xml_against_xsd(validation_employee_xml, self.employees_xsd_path)
        if not is_valid:
            return f"Validation failed: Employee data does not conform to XSD. Details: {validation_error_msg}"

        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if UserID exists
            user_exists_query = f'XQUERY exists(doc("{self.db_name}/users.xml")//User[UserID="{user_id}"])'
            if session.execute(user_exists_query).strip() != "true":
                return f"Cannot create employee: User {user_id} not found."

            # Step 2: Check if EmployeeID already exists
            employee_id_exists_query = f'XQUERY exists(doc("{self.db_name}/employees.xml")//Employee[EmployeeID="{employee_id}"])'
            if session.execute(employee_id_exists_query).strip() == "true":
                return f"Cannot create employee: Employee ID {employee_id} already exists."

            # Step 3: Check if BranchID exists (assuming branches.xml and self.branches_xsd_path exist)
            branch_exists_query = f'XQUERY exists(doc("{self.db_name}/employees.xml")//Employee[BranchID="{branch_id}"])'
            if session.execute(branch_exists_query).strip() != "true":
                # Ensure you have a self.branches_xsd_path and the branches.xml file for this.
                # If branches are not managed in a separate XML, this check should be adapted or removed.
                return f"Cannot create employee: Branch ID {branch_id} not found."

            # Step 4: Insert new employee
            insert_query = f'''
            XQUERY insert node {single_employee_xml}
            into doc("{self.db_name}/employees.xml")/Employees
            '''
            session.execute(insert_query)
            return f"Employee {employee_id} created successfully."

        except Exception as e:
            print(f"Error creating employee: {e} (Type: {type(e).__name__})")
            return f"An error occurred during employee creation: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()


    def update_employee_position(self, employee_id: str, new_position: str, new_salary: Decimal) -> str:
        if not employee_id or not new_position:
             return "Error: Invalid input: employee_id and new_position are required." # ValueError was too harsh for API.
        try:
            salary_str = str(Decimal(new_salary))
            # round the decimal to 2 decimal places
            salary_str = str(Decimal(salary_str).quantize(Decimal('0.01')))  # Round to 2 decimal places
            if Decimal(new_salary) <= 0:
                 return "Error: new_salary must be positive."
        except Exception:
            return "Error: Invalid new_salary format. Expected a number."
        
        # validate that position is a string
        if not isinstance(new_position, str) or not new_position.strip():
            return "Error: Invalid new_position format. Expected a non-empty string."


        session = None
        try:
            session = Session(self.db_host, self.db_port, self.db_user, self.db_pass)
            session.execute(f"OPEN {self.db_name}")

            # Step 1: Check if the employee exists
            employee_exists_query = f'XQUERY exists(doc("{self.db_name}/employees.xml")//Employee[EmployeeID="{employee_id}"])'
            if session.execute(employee_exists_query).strip() != "true":
                return f"Could not update: Employee {employee_id} not found."

            # Step 2: Update position and salary
            # XQuery 1.0 doesn't allow multiple 'replace value of' in one expression directly separated by comma for sequence construction,
            # but BaseX might allow it as separate updating expressions.
            # A safer way for multiple updates if BaseX is strict, is two separate XQuery calls or a FLWOR that reconstructs.
            # However, BaseX is generally flexible with sequences of updating expressions.
            update_query = f'''
            XQUERY (
                replace value of node doc("{self.db_name}/employees.xml")//Employee[EmployeeID="{employee_id}"]/Position with "{new_position}",
                replace value of node doc("{self.db_name}/employees.xml")//Employee[EmployeeID="{employee_id}"]/Salary with xs:decimal("{salary_str}")
            )
            '''
            # If the above XQUERY with a sequence of replace causes issues, execute them separately:
            # update_pos_query = f'XQUERY replace value of node doc("{self.db_name}/employees.xml")//Employee[EmployeeID="{employee_id}"]/Position with "{new_position}"'
            # update_sal_query = f'XQUERY replace value of node doc("{self.db_name}/employees.xml")//Employee[EmployeeID="{employee_id}"]/Salary with xs:decimal("{salary_str}")'
            # session.execute(update_pos_query)
            # session.execute(update_sal_query)

            session.execute(update_query) # Try with combined sequence first
            return f"Employee {employee_id} position and salary updated successfully."

        except Exception as e:
            print(f"Error updating employee {employee_id}: {e} (Type: {type(e).__name__})")
            return f"An error occurred during employee update: {e}"
        finally:
            if session and hasattr(session, 'isconnected') and session.isconnected():
                session.close()
            elif session and hasattr(session, 'close'):
                session.close()


    # ========================================================================
    # Read Queries - 
    # ========================================================================

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user details by UserID using BaseX"""
        query = f'''
        doc("{self.db_name}/users.xml")/Users/User[UserID = "{user_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_single_xml_item(result)

    def get_users_by_role(self, role: str) -> List[Dict]:
        """Get all users with a specific role using BaseX"""
        query = f'''
        doc("{self.db_name}/users.xml")/Users/User[Role = "{role}"]
        '''
        result = self._execute_query(query)
        # Assuming result is <User>...</User><User>...</User>
        return self._parse_xml_string(result, "Users", "User")

    def validate_user_credentials(self, username: str, password_hash: str) -> bool:
        """Validate user credentials using BaseX"""
        # Note: Storing/comparing password hashes directly is insecure. Use proper hashing libraries.
        query = f'''
        exists(
            doc("{self.db_name}/users.xml")/Users/User[Username = "{username}" and PasswordHash = "{password_hash}"]
        )
        '''
        result = self._execute_query(query)
        return result.strip() == 'true'

    def get_accounts_by_user(self, user_id: str) -> List[Dict]:
        """Get all accounts for a specific user using BaseX"""
        query = f'''
        doc("{self.db_name}/accounts.xml")/Accounts/Account[UserID = "{user_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Accounts", "Account")

    def get_account_balance(self, account_id: str) -> Optional[Decimal]:
        """Get current balance of an account using BaseX"""
        query = f'''
        let $bal := doc("{self.db_name}/accounts.xml")/Accounts/Account[AccountID = "{account_id}"]/Balance/text()
        return if (exists($bal)) then $bal else "" (: Return empty string if not found :)
        '''
        result = self._execute_query(query).strip()
        if not result:
            return None
        try:
            # Convert the result to Decimal
            return Decimal(result)
        except ValueError:
            print(f"Could not convert balance '{result}' to Decimal for account {account_id}")
            return None
        


    def get_accounts_by_type(self, account_type: str) -> List[Dict]:
        """Get all accounts of a specific type using BaseX"""
        query = f'''
        doc("{self.db_name}/accounts.xml")/Accounts/Account[AccountType = "{account_type}"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Accounts", "Account")

    def get_transactions_by_account(self, account_id: str,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> List[Dict]:
        """Get transactions for an account with optional date range using BaseX XQuery"""
        # Ensure dates are in ISO format (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD) for xs:dateTime comparison
        query = f'''
        declare variable $accID as xs:string := "{account_id}";
        for $t in doc("{self.db_name}/transactions.xml")/Transactions/Transaction
        where ($t/FromAccountID = $accID or $t/ToAccountID = $accID)
        '''
        # Add date filters - requires Timestamp field to be xs:dateTime compatible
        if start_date:
             # Attempt to parse start_date to ensure it's a valid dateTime or date
             try:
                 datetime.fromisoformat(start_date.replace('Z', '+00:00')) # Validate ISO format
                 query += f' and $t/Timestamp >= xs:dateTime("{start_date}")'
             except ValueError:
                  try: # Try as date
                      datetime.strptime(start_date, '%Y-%m-%d')
                      query += f' and xs:date(substring-before($t/Timestamp, "T")) >= xs:date("{start_date}")'
                  except ValueError:
                      print(f"Warning: Invalid start_date format '{start_date}'. Should be ISO 8601.")

        if end_date:
             # Add 1 day to end_date if only date is provided to include the whole day
             try:
                 dt_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                 query += f' and $t/Timestamp <= xs:dateTime("{end_date}")'
             except ValueError:
                  try: # Try as date, make it end of day
                      dt_end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                      end_date_str = dt_end.strftime('%Y-%m-%d')
                      query += f' and xs:date(substring-before($t/Timestamp, "T")) < xs:date("{end_date_str}")'
                  except ValueError:
                      print(f"Warning: Invalid end_date format '{end_date}'. Should be ISO 8601.")


        query += ' order by $t/Timestamp descending return $t' # Order by date descending

        result = self._execute_query(query)
        return self._parse_xml_string(result, "Transactions", "Transaction")


    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict]:
        """Get a specific transaction by ID using BaseX XQuery"""
        query = f'''
        doc("{self.db_name}/transactions.xml")/Transactions/Transaction[TransactionID = "{transaction_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_single_xml_item(result)

    # --- Loan Queries ---
    def get_loans_by_user(self, user_id: str) -> List[Dict]:
        """Get all loans for a specific user using BaseX"""
        query = f'''
        doc("{self.db_name}/loans.xml")/Loans/Loan[UserID = "{user_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Loans", "Loan")

    def get_approved_loans(self) -> List[Dict]:
        """Get all approved loans (assuming status 'APPROVED') using BaseX"""
        query = f'''
        doc("{self.db_name}/loans.xml")/Loans/Loan[Status = "approved"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Loans", "Loan")

    def get_requested_loans(self) -> List[Dict]:
        """Get all requested loans (assuming status 'REQUESTED') using BaseX"""
        query = f'''
        doc("{self.db_name}/loans.xml")/Loans/Loan[Status = "requested"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Loans", "Loan")

    def get_paid_loans(self) -> List[Dict]:
        """Get all paid loans (assuming status 'PAID') using BaseX"""
        query = f'''
        doc("{self.db_name}/loans.xml")/Loans/Loan[Status = "paid"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Loans", "Loan")

    

    # --- Card Queries ---
    def get_cards_by_account(self, account_id: str) -> List[Dict]:
        """Get all cards associated with an account using BaseX"""
        query = f'''
        doc("{self.db_name}/cards.xml")/Cards/Card[AccountID = "{account_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Cards", "Card")

    def get_active_cards(self) -> List[Dict]:
        """Get all active cards (assuming status 'ACTIVE') using BaseX"""
        query = f'''
        doc("{self.db_name}/cards.xml")/Cards/Card[lower-case(Status) = "active"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Cards", "Card")

    def get_expired_cards(self) -> List[Dict]:
        """Get all expired cards using BaseX"""
        today = datetime.now().strftime('%Y-%m-%d')
        query = f'''
        doc("{self.db_name}/cards.xml")/Cards/Card[xs:date(ExpiryDate) < xs:date("{today}")]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Cards", "Card")

    def get_blocked_cards(self) -> List[Dict]:
        """Get all blocked cards (assuming status 'BLOCKED') using BaseX"""
        query = f'''
        doc("{self.db_name}/cards.xml")/Cards/Card[lower-case(Status) = "blocked"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Cards", "Card")

    # --- Employee Queries ---
    def get_employee_by_id(self, employee_id: str) -> Optional[Dict]:
        """Get employee details by EmployeeID using BaseX"""
        query = f'''
        doc("{self.db_name}/employees.xml")/Employees/Employee[EmployeeID = "{employee_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_single_xml_item(result)

    def get_all_employees(self) -> List[Dict]:
        """Get all employees using BaseX"""
        query = f'''
        doc("{self.db_name}/employees.xml")/Employees/Employee
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Employees", "Employee")

    def get_employees_by_branch(self, branch_id: str) -> List[Dict]:
        """Get all employees in a specific branch using BaseX"""
        query = f'''
        doc("{self.db_name}/employees.xml")/Employees/Employee[BranchID = "{branch_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Employees", "Employee")


    # ==============================================
    # Advanced User Queries (Converted)
    # ==============================================
    def get_users_sorted_by(self, sort_field: str, reverse: bool = False) -> List[Dict]:
        """Get all users sorted by a specific field using XQuery"""
        # Basic validation for sort_field to prevent injection-like issues if needed
        allowed_sort_fields = ["UserID", "FullName", "Email", "Phone", "Role", "Username"]
        if sort_field not in allowed_sort_fields:
            raise ValueError(f"Invalid sort field: {sort_field}")

        order = "descending" if reverse else "ascending"
        # Note: Sorting numbers might need explicit casting in XQuery if they are stored as strings
        # Example: order by xs:integer($u/SomeNumericField)
        query = f'''
        for $u in doc("{self.db_name}/users.xml")/Users/User
        order by $u/{sort_field} {order}
        return $u
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Users", "User")

    def search_users(self, search_term: str, fields: List[str] = ['FullName', 'Email', 'UserID', 'Username', 'Phone']) -> List[Dict]:
        """Search users across multiple fields with case-insensitive matching using XQuery"""
        # Basic validation for fields
        allowed_search_fields = ["UserID", "FullName", "Email", "Phone", "Username", "Role"] # Add Address fields if needed
        valid_fields = [f for f in fields if f in allowed_search_fields]
        if not valid_fields:
            raise ValueError("No valid search fields provided.")

        # Construct the 'contains' part of the where clause dynamically
        # Use lower-case for case-insensitive search
        contains_clauses = [f'contains(lower-case($u/{field}/text()), lower-case("{search_term}"))' for field in valid_fields]
        where_clause = " or ".join(contains_clauses)

        query = f'''
        for $u in doc("{self.db_name}/users.xml")/Users/User
        where {where_clause}
        return $u
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Users", "User")

    # ==============================================
    # Advanced Account Queries (Converted)
    # ==============================================
    def get_accounts_with_min_balance(self, min_balance: Decimal) -> List[Dict]:  # ✅
        """Get accounts with balance greater than or equal to specified amount using XQuery"""
        min_balance_str = str(min_balance)
        query = f'''
        doc("{self.db_name}/accounts.xml")/Accounts/Account[xs:decimal(Balance) >= xs:decimal("{min_balance_str}")]
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Accounts", "Account")

    def get_accounts_sorted_by_balance(self, account_type: Optional[str] = None, reverse: bool = True) -> List[Dict]: # ✅: all sends none
        """Get accounts sorted by balance, optionally filtered by type using XQuery"""
        order = "descending" if reverse else "ascending"
        filter_clause = f'[AccountType = "{account_type}"]' if account_type else ""

        query = f'''
        for $a in doc("{self.db_name}/accounts.xml")/Accounts/Account{filter_clause}
        order by xs:decimal($a/Balance) {order}
        return $a
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Accounts", "Account")

    # ==============================================
    # Advanced Transaction Queries (Converted)
    # ==============================================
    def get_largest_transactions(self, top_n: int = 10) -> List[Dict]:
        if top_n == -1:
            query = f'''
                for $t in doc("{self.db_name}/transactions.xml")/Transactions/Transaction
                order by xs:decimal($t/Amount) descending
                return $t
            '''
        else:
            query = f'''
                let $transactions := 
                    for $t in doc("{self.db_name}/transactions.xml")/Transactions/Transaction
                    order by xs:decimal($t/Amount) descending
                    return $t
                return $transactions[position() <= {top_n}]
            '''

        result = self._execute_query(query)
        return self._parse_xml_string(result, "Transactions", "Transaction")

    def get_transaction_stats(self, account_id: str) -> Dict:
        """Get statistics for transactions on an account using XQuery"""
        # This query aggregates directly in XQuery
        query = f'''
        declare variable $accID as xs:string := "{account_id}";
        let $transactions := doc("{self.db_name}/transactions.xml")/Transactions/Transaction
                           [FromAccountID = $accID or ToAccountID = $accID]
        let $amounts := $transactions/Amount ! xs:decimal(.) (: Convert amounts to decimal :)
        let $count := count($transactions)
        return
          if ($count > 0) then
            <stats>
              <count>{{$count}}</count>
              <total>{{sum($amounts)}}</total>
              <average>{{avg($amounts)}}</average>
              <max>{{max($amounts)}}</max>
              <min>{{min($amounts)}}</min>
              <last_date>{{max($transactions/Timestamp/text())}}</last_date> (: Assumes text sort matches date sort :)
            </stats>
          else <stats/> (: Return empty stats element if no transactions :)
        '''
        result = self._execute_query(query)
        parsed = self._parse_single_xml_item(result)

        # Convert numeric stats from string back to Decimal/int if needed by caller
        if parsed:
            for key in ['total', 'average', 'max', 'min']:
                 if key in parsed and parsed[key] is not None:
                     try:
                         parsed[key] = Decimal(parsed[key])
                     except: pass # Keep as string if conversion fails
            if 'count' in parsed and parsed['count'] is not None:
                try:
                     parsed['count'] = int(parsed['count'])
                except: pass
        return parsed if parsed else {} # Return empty dict if no stats found


    def detect_high_value_transactions( self,threshold: Decimal, days: int = 7) -> List[Dict]:
        """Detect high value transactions in recent period using XQuery"""
        threshold_str = str(threshold)
        end_date = datetime.now() # Use current time
        start_date = end_date - timedelta(days=float(days))  # preserves decimals
        start_date_str = start_date.isoformat()

        query = f'''
        declare variable $thresh as xs:decimal := xs:decimal("{threshold_str}");
        declare variable $startDate as xs:dateTime := xs:dateTime("{start_date_str}");

        for $t in doc("{self.db_name}/transactions.xml")/Transactions/Transaction
        where xs:decimal($t/Amount) >= $thresh
        and xs:dateTime($t/Date) >= $startDate
        order by xs:decimal($t/Amount) descending, $t/Date descending
        return $t
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Transactions", "Transaction")


    # ==============================================
    # Cross-Entity Queries (Joins) - More Complex in XQuery
    # ==============================================
    # These often require joining data within the XQuery or making multiple calls

    def get_user_with_accounts_and_transactions(self, user_id: str) -> Optional[Dict]:
        """Get complete user profile with accounts and recent transactions (multiple queries)"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        accounts = self.get_accounts_by_user(user_id)
        total_balance = Decimal(0)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

        for account in accounts:
            # Get recent transactions for each account
            account['transactions'] = self.get_transactions_by_account(
                account['AccountID'],
                start_date=thirty_days_ago
            )
            # Calculate total balance
            try:
                total_balance += Decimal(account.get('Balance', 0))
            except:
                 pass # Ignore if balance is missing or invalid

        user['accounts'] = accounts
        user['total_balance'] = total_balance # Add calculated total balance
        return user



    def get_employee_performance(self, branch_id: str) -> List[Dict]:
        """Get employee performance metrics by branch (loan counts) (multiple queries)"""
        employees = self.get_employees_by_branch(branch_id)
        if not employees:
            return []

        results = []
        for emp in employees:
            user_id = emp.get('UserID')
            if not user_id:
                continue # Skip employee if UserID is missing

            # Get user details (for name)
            user = self.get_user_by_id(user_id)
            user_name = user.get('FullName', 'N/A') if user else 'N/A'

            # Get loans associated with this employee's UserID
            loans = self.get_loans_by_user(user_id)
            approved_loans = [l for l in loans if l.get('Status') == 'APPROVED']
            total_loan_amount = sum(Decimal(l.get('Amount', 0)) for l in loans)

            results.append({
                'employee_id': emp.get('EmployeeID'),
                'name': user_name,
                'position': emp.get('Position'),
                'hire_date': emp.get('HireDate'),
                'total_loans_processed': len(loans),
                'approved_loans': len(approved_loans),
                'total_loan_amount': total_loan_amount
            })

        # Sort by total loan amount descending
        return sorted(results, key=lambda x: x['total_loan_amount'], reverse=True)

        # Alternative XQuery approach (complex join):
        # Could construct the result XML directly in XQuery by joining
        # employees, users, and loans documents based on UserID.


    # ==============================================
    # Business Intelligence Queries (Converted where feasible)
    # ==============================================

    def get_customer_segments(self, balance_thresholds: Optional[List[Decimal]] = None) -> Dict:
        """Segment customers by total account balance (multiple queries)"""
        # Default to 3 segments if no thresholds are provided
        if balance_thresholds is None:
            balance_thresholds = [Decimal(1000), Decimal(5000), Decimal(10000)]

        # 1. Get all customer UserIDs
        query_users = f'''
        for $u in doc("{self.db_name}/users.xml")/Users/User[Role='customer']
        return $u/UserID/text()
        '''
        user_ids_str = self._execute_query(query_users)
        user_ids = user_ids_str.split()  # BaseX returns space-separated text() nodes

        # Initialize segments
        segments = {f"< {threshold}": 0 for threshold in sorted(balance_thresholds)}
        segments[f">= {sorted(balance_thresholds)[-1]}"] = 0  # Highest threshold segment

        # 2. For each user, get total balance
        for user_id in user_ids:
            if not user_id:
                continue
            # Get all accounts for the user
            accounts = self.get_accounts_by_user(user_id)
            balance = sum(Decimal(acc.get('Balance', 0)) for acc in accounts)

            # Assign to segment
            assigned = False
            for threshold in sorted(balance_thresholds):
                if balance < threshold:
                    segments[f"< {threshold}"] += 1
                    assigned = True
                    break
            if not assigned:
                segments[f">= {sorted(balance_thresholds)[-1]}"] += 1

        return segments


    def get_transaction_volume_report(self, period: str = 'month') -> List[Dict]:
        """Get transaction volume report by time period using XQuery grouping"""
        # Choose the grouping format based on the period
        period_format = {
            'day': 'xs:date(substring($t/Date, 1, 10))', # YYYY-MM-DD
            'month': 'substring($t/Date, 1, 7)',         # YYYY-MM
            'year': 'substring($t/Date, 1, 4)'           # YYYY
            # Week grouping is complex in pure XQuery, might need external processing
            # or specific BaseX date functions if available.
        }.get(period)

        if not period_format:
            raise ValueError("Unsupported period. Choose 'day', 'month', or 'year'.")

        query = f'''
        for $t in doc("{self.db_name}/transactions.xml")/Transactions/Transaction
        let $periodKey := {period_format}
        group by $periodKey
        order by $periodKey ascending
        return <periodData>
                 <period>{{$periodKey}}</period>
                 <count>{{count($t)}}</count>
                 <amount>{{sum($t/Amount ! xs:decimal(.))}}</amount>
               </periodData>
        '''
        result = self._execute_query(query)
        parsed_data = self._parse_xml_string(result, "Results", "periodData")

        # Convert amount back to Decimal
        for item in parsed_data:
             if 'amount' in item and item['amount'] is not None:
                 try:
                     item['amount'] = Decimal(item['amount'])
                 except: pass # Keep as string if conversion fails
             if 'count' in item and item['count'] is not None:
                try:
                     item['count'] = int(item['count'])
                except: pass
        return parsed_data

    def get_top_customers(self, top_n: int = 10) -> List[Dict]:
        """Get top customers by total balance using XQuery"""
        query = f'''
        for $u in doc("{self.db_name}/users.xml")/Users/User[Role='customer']
        let $userID := $u/UserID/text()
        let $accounts := doc("{self.db_name}/accounts.xml")/Accounts/Account[UserID = $userID]
        let $totalBalance := sum($accounts/Balance ! xs:decimal(.))
        order by $totalBalance descending
        return <Customer>
                 <UserID>{{$userID}}</UserID>
                 <FullName>{{$u/FullName/text()}}</FullName>
                 <TotalBalance>{{$totalBalance}}</TotalBalance>
               </Customer>
        '''
        result = self._execute_query(query)
        parsed_data = self._parse_xml_string(result, "Customers", "Customer")
        
        # Limit to top_n results
        return parsed_data[:top_n] if parsed_data else []
    # ==============================================
    # Card Management Queries (Converted)
    # ==============================================

    def get_expiring_cards(self, months: int = 1) -> List[Dict]:
        """Get cards expiring within the next X months using XQuery"""

        today = datetime.now().date()
        # Calculate future date precisely
        future_month = today.month + months
        future_year = today.year + (future_month - 1) // 12
        future_month = (future_month - 1) % 12 + 1
        # Find the last day of the target month
        # A bit tricky, get first day of *next* month, subtract one day
        next_month_year = future_year + (future_month // 12)
        next_month_month = (future_month % 12) + 1
        first_day_of_next_month = datetime(next_month_year, next_month_month, 1)
        last_day_of_future_month = first_day_of_next_month - timedelta(days=1)

        today_str = today.strftime('%Y-%m-%d')
        future_date_str = last_day_of_future_month.strftime('%Y-%m-%d')


        # Query joins Card -> Account -> User info within XQuery
        query = f'''
        declare variable $today as xs:date := xs:date("{today_str}");
        declare variable $futureDate as xs:date := xs:date("{future_date_str}");

        for $card in doc("{self.db_name}/cards.xml")/Cards/Card
        let $expiryDate := xs:date($card/ExpiryDate)
        where $expiryDate >= $today and $expiryDate <= $futureDate
        let $account := doc("{self.db_name}/accounts.xml")/Accounts/Account[AccountID = $card/AccountID]
        let $user := doc("{self.db_name}/users.xml")/Users/User[UserID = $account/UserID]
        order by $expiryDate ascending
        return <CardInfo>
                 {{ $card/* }} (: Copy all elements from card :)
                 <AccountType>{{$account/AccountType/text()}}</AccountType>
                 <UserID>{{$user/UserID/text()}}</UserID>
                 <UserName>{{$user/FullName/text()}}</UserName>
               </CardInfo>
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "ExpiringCards", "CardInfo")

    def get_all_transactions(self) -> List[Dict]:
        """Get all transactions using XQuery"""
        query = f'''
        doc("{self.db_name}/transactions.xml")/Transactions/Transaction
        '''
        result = self._execute_query(query)
        return self._parse_xml_string(result, "Transactions", "Transaction")
        
    # ==============================================
    # Helper Methods (Adjusted)
    # ==============================================

    def _get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Internal method to get account by ID using BaseX"""
        query = f'''
        doc("{self.db_name}/accounts.xml")/Accounts/Account[AccountID = "{account_id}"]
        '''
        result = self._execute_query(query)
        return self._parse_single_xml_item(result)


    def _element_to_dict(self, element: ET.Element) -> Dict:
        """Convert an xml.etree.ElementTree element to a dictionary with typed values"""
        result = {}
        if element is None:
            return result

        for child in element:
            tag = child.tag
            text = child.text.strip() if child.text else None

            # Handle nested elements (like Address)
            if len(child) > 0:
                 result[tag] = self._element_to_dict(child) # Recursive call
            elif text is not None:
                # Try to convert to appropriate type based on tag naming convention
                try:
                    if tag in ['Balance', 'Amount', 'InterestRate', 'Salary']:
                        result[tag] = Decimal(text)
                    elif tag in ['Duration', 'count']: # Example numeric fields
                         result[tag] = int(text)
                    # Add more type conversions as needed (e.g., boolean, dates)
                    # elif tag in ['Timestamp', 'Date', 'StartDate', 'HireDate', 'ExpiryDate', 'OpenDate']:
                    #    result[tag] = text # Keep date/time strings as is for now
                    else:
                        result[tag] = text
                except (ValueError, TypeError):
                    # Keep as string if conversion fails
                    result[tag] = text
            else:
                 result[tag] = None # Keep null/empty elements as None

        return result

    # _parse_date helper might not be needed if dates are handled within XQuery or kept as strings
    # def _parse_date(self, date_str: str) -> Optional[datetime]: ...

