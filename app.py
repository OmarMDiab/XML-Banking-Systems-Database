# banking_ui.py
import streamlit as st
from Banking_xml_queries import BankingXMLQueries
from decimal import Decimal
import pandas as pd
import random
from datetime import datetime

# Initialize banking system
# Check for database credentials in session state
if 'db_creds' not in st.session_state:
    st.title("🔒 Database Authentication")
    st.markdown("""
    <style>
        .form-title {
            text-align: center;
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .form-submit {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        .form-submit:hover {
            background-color: #45a049;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.form("database_login", clear_on_submit=True):
        st.markdown('<div class="form-title">Enter Database Credentials</div>', unsafe_allow_html=True)

        # Default values for host and port
        DEFAULT_HOST = 'localhost'
        DEFAULT_PORT = 1984

        # Input fields for username and password
        db_user = st.text_input("👤 Username", placeholder="Enter your username")
        db_pass = st.text_input("🔑 Password", type="password", placeholder="Enter your password")

        # Submit button
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            try:
                # Test connection with default host and port
                test_bank = BankingXMLQueries(
                    db_user=db_user,
                    db_pass=db_pass,
                    db_host=DEFAULT_HOST,
                    db_port=DEFAULT_PORT
                )
                test_bank.get_users_by_role("customer")  # Test query to validate credentials

                # Store credentials in session state
                st.session_state.db_creds = {
                    'user': db_user,
                    'pass': db_pass,
                    'host': DEFAULT_HOST,
                    'port': DEFAULT_PORT
                }
                st.success("✅ Authentication successful! Redirecting...")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Authentication failed: {str(e)}")

        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# Initialize banking system with stored credentials (including hidden defaults)
bank = BankingXMLQueries(
    db_user=st.session_state.db_creds['user'],
    db_pass=st.session_state.db_creds['pass'],
    db_host=st.session_state.db_creds['host'],
    db_port=st.session_state.db_creds['port']
)

# Configure page
st.set_page_config(
    page_title="Banking System Manager",
    page_icon="🏦",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {padding: 2rem;}
    .stButton>button {width: 100%;}
    .stSelectbox, .stTextInput {margin-bottom: 1rem;}
    .success {color: #2ecc71;}
    .error {color: #e74c3c;}
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("Navigation")
section = st.sidebar.radio("Select Section", [
    "Dashboard",
    "Customer Management",
    "Account Operations",
    "Transaction Processing",
    "Loan Administration",
    "Card Services",
    "Employee Management",
    "Analytics & Reports"
])

# Helper functions
def display_result(message, success=True):
    if success:
        st.markdown(f'<p class="success">✓ {message}</p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p class="error">✗ {message}</p>', unsafe_allow_html=True)

# Main Content
if section == "Dashboard":
    st.title("Banking System Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.subheader("Customers")
        customers = bank.get_users_by_role("customer")
        st.metric("Total Customers", len(customers))
    
    with col2:
        st.subheader("Accounts")
        accounts = bank.get_accounts_by_type("savings") + bank.get_accounts_by_type("checking")
        st.metric("Total Accounts", len(accounts))


    
    with col3:
        st.subheader("Transactions")
        transactions = bank.get_largest_transactions(-1)
        st.metric("Total Transactions", len(transactions))

    with col4:
        st.subheader("Loans")
        loans = bank.get_requested_loans() + bank.get_approved_loans() + bank.get_paid_loans()
        st.metric("Total Loans", len(loans))

    st.divider()
    st.subheader("Recent Activities")
    transactions = bank.get_largest_transactions(-1)
    st.dataframe(pd.DataFrame(transactions), use_container_width=True)

elif section == "Customer Management":
    st.title("Customer Management")
    tab1,tabx, tab2 = st.tabs(["Create Customer","Customers Database", "Search/Edit Customers"])
    
    with tab1:
        with st.form("create_customer"):
            st.subheader("New Customer Registration")
            email = st.text_input("Email")
            full_name = st.text_input("Full Name")
            phone = st.text_input("Phone Number")
            col1, col2, col3 = st.columns(3)
            with col1:
                country = st.text_input("Country")
            with col2:
                city = st.text_input("City")
            with col3:
                street = st.text_input("Street")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Create Customer"):
                if email and full_name and phone:
                    result = bank.create_user({
                        "Email": email,
                        "FullName": full_name,
                        "Phone": phone,
                        "Address": {"Country": country, "City": city, "Street": street},
                        "Role": "customer",
                        "Username": username,
                        "PasswordHash": password
                    })
                    display_result(result)
                else:
                    display_result("Missing required fields", False)
    with tabx:
        st.subheader("Customer Database")
        customers = bank.get_users_by_role("customer")
        if customers:
            df = pd.DataFrame(customers)
            df["Address"] = df["Address"].apply(lambda x: f"{x['Street']}, {x['City']}, {x['Country']}")
            st.dataframe(df[["UserID","Username", "FullName", "Email", "Phone","Address"]], use_container_width=True)
        else:
            st.info("No customers found")

    with tab2:
        st.subheader("Customer's Accounts & Loans")
        search_term = st.text_input("Search by name, email, or phone")
        if search_term:
            results = bank.search_users(search_term)
            df = pd.DataFrame(results)
            if not df.empty:
                st.dataframe(df[["UserID", "FullName", "Email", "Phone"]], use_container_width=True)
                
                selected = st.selectbox("Select Customer", df["UserID"])
                if selected:
                    customer = bank.get_user_by_id(selected)
                    with st.expander("Edit Customer Details"):
                        with st.form("update_customer"):
                            new_email = st.text_input("Email", customer.get("Email"))
                            new_phone = st.text_input("Phone", customer.get("Phone"))
                            new_full_name = st.text_input("Full Name", customer.get("FullName"))
                            new_username = st.text_input("Username", customer.get("Username"))
                            if st.form_submit_button("Update Details"):
                                result = bank.update_user(selected, {
                                    "Email": new_email,
                                    "Phone": new_phone,
                                    "FullName": new_full_name,
                                    "Address": customer["Address"],  # Address remains unchanged
                                    "Role": "customer",
                                    "Username": new_username,
                                    "PasswordHash": customer["PasswordHash"]  # Password remains unchanged
                                })
                                display_result(result)
                                st.rerun()
                    st.divider()
                    st.subheader("Customer Accounts")
                    accounts = bank.get_accounts_by_user(selected)
                    if accounts:
                        st.dataframe(pd.DataFrame(accounts), use_container_width=True)
                    else:
                        st.info("No accounts found for this customer")

                    st.divider()
                    st.subheader("Customer Loans")
                    loans = bank.get_loans_by_user(selected)
                    if loans:
                        st.dataframe(pd.DataFrame(loans), use_container_width=True)
                    else:
                        st.info("No loans found for this customer")

            else:
                st.info("No customers found")

elif section == "Account Operations":
    st.title("Account Management")
    tab1, tab2, tab3 = st.tabs(["Create Account", "Account Services","Accounts Reports"])
    
    with tab1:
        with st.form("create_account"):
            st.subheader("New Account Opening")
            user_id = st.text_input("Customer ID")
            acc_type = st.selectbox("Account Type", ["savings", "checking"])
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])
            deposit = st.number_input("Initial Deposit", min_value=0.0)
            
            if st.form_submit_button("Create Account"):
                result = bank.create_account({
                    "UserID": user_id,
                    "AccountType": acc_type,
                    "Balance": deposit,
                    "Currency": currency
                })
                display_result(result)
    
    with tab2:
        account_id = st.text_input("🔐 Enter Account ID", placeholder="e.g. ACC123456")

        if account_id:
            account = bank._get_account_by_id(account_id)

            if account:
                # Capitalize and normalize status for easier checks
                account_status = account['Status'].strip().lower()

                st.markdown("### 💼 Account Summary")

                # Status Badge
                status_color = "green" if account_status == "active" else "red"
                status_label = f"<span style='color:{status_color}; font-weight:bold;'>{account['Status'].capitalize()}</span>"
                st.markdown(f"🔑 **Account ID:** {account['AccountID']}")

                st.markdown(f"🔄 **Status:** {status_label}", unsafe_allow_html=True)
                # write acc id
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.success(f"**Account Type:** {account['AccountType'].capitalize()}")
                    st.info(f"**User ID:** {account['UserID']}")
                    st.markdown(f"📅 **Open Date:** {account['OpenDate']}")
                with col2:
                    st.metric(label="💰 Current Balance", value=f"{account['Balance']} {account['Currency']}")

                st.divider()

                # Display linked cards
                st.markdown("### 💳 Linked Cards")
                cards = bank.get_cards_by_account(account['AccountID'])
                if cards:
                    df = pd.DataFrame(cards)
                    df['ExpiryDate'] = pd.to_datetime(df['ExpiryDate']).dt.strftime('%m/%Y')
                    st.dataframe(
                        df[['CardID', 'CardType', 'CardNumber', 'ExpiryDate', 'Status']],
                        use_container_width=True
                    )
                else:
                    st.info("No cards linked to this account.")

                st.divider()
                st.markdown("### 📈 Transaction Overview")
                transactions = bank.get_transactions_by_account(account_id)

                if transactions:
                    df = pd.DataFrame(transactions)

                    if 'Date' in df.columns:
                        
                        df['Date'] = pd.to_datetime(df['Date'])

                    if 'Amount' in df.columns and 'Date' in df.columns:
                        df_sorted = df.sort_values(by='Date')
                        st.line_chart(df_sorted.set_index('Date')['Amount'])
                    else:
                        st.info("✅ Transactions found, but no plot-compatible fields.")
                else:
                    st.warning("⚠️ No transactions found for this account.")

                st.divider()

                # Show close button only if account is active
                if account_status != "closed":
                    st.markdown("### ⚠️ Dangerous Actions")
                    if st.button("🗑️ Close Account", use_container_width=True):
                        result = bank.close_account(account_id)
                        display_result(result)
                        st.rerun()
                else:
                    st.markdown("<p style='text-align: center;'>This account is already <strong>closed</strong> and cannot be modified.</p>", unsafe_allow_html=True)
            else:
                st.error("❌ Account not found. Please double-check the Account ID.")
    with tab3:
        st.subheader("Accounts Database")
        # col1, col2 = st.columns(2)

        with st.container():
            min_balance = st.number_input("Minimum Balance", min_value=0.0, value=0.0)
            if st.button("Filter Accounts by Balance"):
                accounts = bank.get_accounts_with_min_balance(Decimal(min_balance))
                if accounts:
                    df = pd.DataFrame(accounts)
                    st.dataframe(df[["AccountID", "UserID", "AccountType", "Balance", "Currency"]], use_container_width=True)
                else:
                    st.info("No accounts found with the specified minimum balance.")
        st.divider()

        with st.container():
            account_type = st.selectbox("Account Type", ["All", "savings", "checking"])
            reverse = st.checkbox("Sort by Balance Descending", value=True)
            if st.button("Sort Accounts by Balance"):
                account_type_filter = None if account_type == "All" else account_type
                accounts = bank.get_accounts_sorted_by_balance(account_type_filter, reverse)
                if accounts:
                    df = pd.DataFrame(accounts)
                    st.dataframe(df[["AccountID", "UserID", "AccountType", "Balance", "Currency"]], use_container_width=True)
                else:
                    st.info("No accounts found for the specified criteria.")

elif section == "Transaction Processing":
    st.title("Transaction Processing")
    tab1, tab2, tab3 = st.tabs([
        "New Transaction",
        "Transactions Database & Overview",
        "Transaction Monitoring"
    ])
    
    with tab1:
        st.subheader("New Transaction")
        with st.form("new_transaction"):
            from_acc = st.text_input("From Account")
            to_acc = st.text_input("To Account")
            amount = st.number_input("Amount", min_value=0.01)
            tx_type = st.selectbox("Transaction Type", [
                "transfer", "payment", "withdrawal", "deposit"
            ])
            
            if st.form_submit_button("Process Transaction"):
                result = bank.create_transaction({
                    "FromAccountID": from_acc,
                    "ToAccountID": to_acc,
                    "Amount": amount,
                    "Type": tx_type
                })
                display_result(result)

    with tab2:
        st.subheader("Transactions Database & Overview")
        transactions = bank.get_all_transactions()
        if transactions:
            df = pd.DataFrame(transactions)
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            st.subheader("Transaction Statistics")
            if "Amount" in df.columns:
                total_transactions = len(df)
                total_amount = df["Amount"].sum()
                avg_transaction = df["Amount"].mean()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transactions", total_transactions)
                with col2:
                    st.metric("Total Amount", f"${total_amount:,.2f}")
                with col3:
                    st.metric("Average Transaction", f"${avg_transaction:,.2f}")
            else:
                st.info("No numeric data available for statistics.")
        else:
            st.info("No transactions found in the database.")

    with tab3:
        st.subheader("Transaction Monitoring")
        threshold = st.number_input("Set Alert Threshold", min_value=1000.0, value=5000.0)
        time_unit = st.selectbox("Select Time Unit", ["days", "months", "years"], index=0)
        time_period = st.number_input("Set Time Period", min_value=1, value=7)

        # Convert the time period to days
        if time_unit == "months":
            time_period_in_days = time_period * 30  # Approximation: 1 month = 30 days
        elif time_unit == "years":
            time_period_in_days = time_period * 365  # Approximation: 1 year = 365 days
        else:
            time_period_in_days = time_period

        if threshold and time_period_in_days:
            from decimal import Decimal
            alerts = bank.detect_high_value_transactions(Decimal(threshold), days=int(time_period_in_days))
            if alerts:
                st.warning(f"High Value Transactions (> {threshold}) in the last {time_period} {time_unit}")
                st.dataframe(pd.DataFrame(alerts), use_container_width=True)
            else:
                st.info(f"No high value transactions detected in the last {time_period} {time_unit}.")


elif section == "Loan Administration":
    st.title("Loan Management")
    tab1, tab2 = st.tabs(["New Loan Application", "Loans management"])
    
    with tab1:
        with st.form("new_loan"):
            st.subheader("Loan Application")
            user_id = st.text_input("Customer ID")
            amount = st.number_input("Loan Amount", min_value=1000.0)
            duration = st.selectbox("Term (months)", [12, 24, 36, 60])
            interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1)
            
            if st.form_submit_button("Submit Application"):
                result = bank.create_loan({
                    "UserID": user_id,
                    "LoanAmount": amount,
                    "Duration": f"{duration} months",
                    "InterestRate": interest_rate
                })
                display_result(result)
    
    with tab2:
        st.subheader("Requested Loans")
        requested_loans = bank.get_requested_loans()
        if requested_loans:
            df = pd.DataFrame(requested_loans)
            st.dataframe(df, use_container_width=True)
            
            selected = st.selectbox("Select Loan to Approve", df["LoanID"])
            if st.button("Approve Loan"):
                result = bank.approve_loan(selected)
                display_result(result)
                # delay for 2 seconds to show the result
                st.rerun()
        else:
            st.info("No active loans in the system")

        

        st.divider()
        st.subheader("Approved Loans")
        approved_loans = bank.get_approved_loans()
        if approved_loans:
            df = pd.DataFrame(approved_loans)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No approved loans in the system")
        st.divider()
        st.subheader("Paid Loans")
        paid_loans = bank.get_paid_loans()
        if paid_loans:
            df = pd.DataFrame(paid_loans)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No paid loans in the system")
        

elif section == "Card Services":
    st.title("Card Management")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["Create New Card", "Manage Cards", "Card Reports"])
    
    with tab1:
        st.subheader("Issue New Card")
        with st.form("new_card", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                account_id = st.text_input("Linked Account ID*")
                card_type = st.selectbox("Card Type*", ["Visa", "Mastercard", "Amex"])
                card_number = st.text_input("Card Number*")
            with col2:
                expiry = st.date_input("Expiration Date*", 
                            min_value=datetime.today(),
                            format="YYYY-MM-DD")
                cvv_display = st.empty()
                cvv = st.text_input("CVV*", max_chars=3)
            
            if st.form_submit_button("✨ Issue New Card"):
                required = ['AccountID', 'CardType', 'CardNumber', 'CVV', 'ExpiryDate']
            if not all([account_id, card_type, card_number, cvv, expiry]):
                display_result("All fields are required!", False)
            else:
                account = bank._get_account_by_id(account_id)
                if not account:
                    display_result("Account not found!", False)
                else:
                    expiry_date = f"{expiry.year}-{expiry.month:02d}-01"
                    result = bank.create_card({
                        "AccountID": account_id,
                        "CardType": card_type,
                        "CardNumber": card_number,
                        "CVV": cvv,
                        "ExpiryDate": expiry_date
                    })
                    display_result(result)

    with tab2:
            
        with st.container(border=False):
            st.markdown("### Block Card")
            with st.form("cancel_card_form"):
                card_id = st.text_input("**Enter Card ID to Block:**")
                if st.form_submit_button("🛑 Block Card"):
                    if card_id:
                        result = bank.block_card(card_id)
                        display_result(result)
                    else:
                        display_result("Card ID is required!", False)
        #st.divider()
        with st.container(border=False):
            st.markdown("### Search Cards")
            with st.form("search_cards_form"):
                search_account = st.text_input("**Account ID:**")
                if st.form_submit_button("🔍 Search Cards"):
                    if search_account:
                        cards = bank.get_cards_by_account(search_account)
                        if cards:
                            df = pd.DataFrame(cards)[['CardID', 'CardType', 'ExpiryDate', 'Status']]
                            st.dataframe(
                                df.style.format({'ExpiryDate': lambda x: pd.to_datetime(x).strftime('%m/%Y')}),
                                use_container_width=True,
                                height=200
                            )
                        else:
                            st.info("No cards found for this account")
                    else:
                        st.warning("Please enter an Account ID")

    with tab3:
        st.subheader("Card Analytics")
        
        with st.container(border=True):
            st.markdown("### 🟢 Active Cards Overview")
            active_cards = bank.get_active_cards()
            if active_cards:
                df = pd.DataFrame(active_cards)
                df['ExpiryDate'] = pd.to_datetime(df['ExpiryDate']).dt.strftime('%m/%Y')
                st.dataframe(
                    df[['CardID', 'AccountID', 'CardType','CardNumber', 'ExpiryDate']],
                    use_container_width=True,
                    height=400
                )
            else:
                st.info("No active cards found")
        
        with st.container(border=True):
            st.markdown("### 🟠 Expiring Cards (Next 3 Months) ~ adv Qeury")
            expiring = bank.get_expiring_cards(3)
            if expiring:
                df = pd.DataFrame(expiring)
                df['Expiry'] = pd.to_datetime(df['ExpiryDate']).dt.strftime('%m/%Y')
                df['Days Left'] = (pd.to_datetime(df['ExpiryDate']) - datetime.today()).dt.days
                st.dataframe(
                    df[['CardID', 'AccountID','CardType','CardNumber', 'Expiry', 'Days Left']]
                    .sort_values('Days Left', ascending=True),
                    use_container_width=True,
                    height=300
                )
            else:
                st.info("No cards expiring in next 3 months")
        
        with st.container(border=True):
            st.markdown("### 🔴 Expired Cards")
            expired_cards = bank.get_expired_cards()
            if expired_cards:
                df = pd.DataFrame(expired_cards)
                df['ExpiryDate'] = pd.to_datetime(df['ExpiryDate']).dt.strftime('%m/%Y')
                st.dataframe(
                    df[['CardID', 'AccountID','CardType','CardNumber', 'ExpiryDate']],
                    use_container_width=True,
                    height=300
                )
            else:
                st.info("No expired cards found")
        
        with st.container(border=True):
            st.markdown("### 🛑 Blocked Cards")
            blocked_cards = bank.get_blocked_cards()
            if blocked_cards:
                df = pd.DataFrame(blocked_cards)
                st.dataframe(
                    df[['CardID', 'AccountID','CardType','CardNumber', 'Status']],
                    use_container_width=True,
                    height=300
                )
            else:
                st.info("No blocked cards found")

elif section == "Employee Management":
    st.title("Staff Administration")
    tab1, tab2, tab3 = st.tabs(["Add Employee", "Employee Directory", "Branch's Employees"])
    
    with tab1:
        with st.form("new_employee"):
            st.subheader("New Employee Onboarding")
            
            # User creation fields
            st.markdown("### User Details")
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone Number")
            col1, col2, col3 = st.columns(3)
            with col1:
                country = st.text_input("Country")
            with col2:
                city = st.text_input("City")
            with col3:
                street = st.text_input("Street")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            # Employee-specific fields
            st.markdown("### Employee Details")
            position = st.selectbox("Position", [
                "Teller", "Loan Officer", "Manager", "Financial Advisor"
            ])
            branch_id = st.text_input("Branch ID")
            salary = st.number_input("Salary", min_value=2000)
            
            if st.form_submit_button("Create Employee Record"):
                # Validate user fields
                if not all([full_name, email, phone, country, city, street, username, password]):
                    display_result("All user fields are required!", False)
                else:
                    # Create user
                    user_data = {
                        "FullName": full_name,
                        "Email": email,
                        "Phone": phone,
                        "Address": {"Country": country, "City": city, "Street": street},
                        "Role": "employee",
                        "Username": username,
                        "PasswordHash": password
                    }
                    user_result = bank.create_user(user_data)
                    
                    if "successfully" in user_result.lower():
                        # Extract UserID from the success message
                        user_id = user_result.split()[1]
                        
                        # Create employee
                        employee_data = {
                            "UserID": user_id,
                            "Position": position,
                            "BranchID": branch_id,
                            "Salary": salary
                        }
                        employee_result = bank.create_employee(employee_data)
                        display_result(employee_result)
                    else:
                        display_result(user_result, False)
    
    with tab2:
        st.subheader("Employee Directory")
        employees = bank.get_all_employees()
        if employees:
            employee_df = pd.DataFrame(employees)
            users = bank.get_users_by_role("employee")
            user_df = pd.DataFrame(users)
            
            # Merge employee and user dataframes on UserID
            merged_df = pd.merge(employee_df, user_df, on="UserID", how="inner")
            
            # Format Address if present
            if "Address" in merged_df.columns:
                merged_df["Address"] = merged_df["Address"].apply(
                    lambda x: f"{x['Street']}, {x['City']}, {x['Country']}" if isinstance(x, dict) else x
                )
            
            # Display merged dataframe
            st.dataframe(
                merged_df[["UserID", "FullName", "Position", "BranchID", "Salary", "Address", "Email", "Phone"]],
                use_container_width=True
            )
    
    with tab3:
        st.subheader("Branches Employess")
        branch_id = st.text_input("Branch ID")
        if branch_id:
            performance_data = bank.get_employee_performance(branch_id)
            if performance_data:
                df = pd.DataFrame(performance_data)
                st.dataframe(
                    df[["employee_id", "name", "position", "hire_date"]],
                    use_container_width=True
                )
            else:
                st.info("No performance data found for the specified branch.")

elif section == "Analytics & Reports":
    st.title("Business Intelligence")
    tab1, tab2, tab3 = st.tabs([
        "Bank Overview", 
        "Customer Insights", 
        "Transaction Analysis"
    ])
    
    with tab1:
        # st.subheader("Financial Health")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.subheader("Customers")
            customers = bank.get_users_by_role("customer")
            st.metric("Total Customers", len(customers))
        
        with col2:
            st.subheader("Accounts")
            accounts = bank.get_accounts_by_type("savings") + bank.get_accounts_by_type("checking")
            st.metric("Total Accounts", len(accounts))

        with col3:
            st.subheader("Transactions")
            transactions = bank.get_largest_transactions(-1)
            st.metric("Total Transactions", len(transactions))

        with col4:
            st.subheader("Loans")
            loans = bank.get_requested_loans() + bank.get_approved_loans() + bank.get_paid_loans()
            st.metric("Total Loans", len(loans))

        st.divider()
        st.subheader("Top Customers by Total Balance in all of his accounts")
        top_n = st.text_input("Enter the number of top customers to display", value="5")
        if top_n.isdigit() and int(top_n) > 0:
            top_customers = bank.get_top_customers(top_n=int(top_n))
            if top_customers:
                df = pd.DataFrame(top_customers)
                st.dataframe(df[["UserID", "FullName", "TotalBalance"]], use_container_width=True)
            else:
                st.info("No data available for top customers.")
        else:
            st.warning("Please enter a valid positive number.")


    
    with tab2:
        st.subheader("Customer Segmentation")
        segments = bank.get_customer_segments()
        st.bar_chart(pd.DataFrame.from_dict(segments, orient='index'))
    
    with tab3:
        st.subheader("Transaction Trends")
        vol_report = bank.get_transaction_volume_report('month')
        df = pd.DataFrame(vol_report)
        st.line_chart(df.set_index('period'))

# Run the app
if __name__ == "__main__":
    divider = st.markdown("<hr>", unsafe_allow_html=True)
    # add the logged in user creds['user']
    user = st.session_state.db_creds['user']
    st.markdown(f"<h3 style='text-align: center;'>Welcome, {user}! Banking System Database Management 🏦</h3>", unsafe_allow_html=True)