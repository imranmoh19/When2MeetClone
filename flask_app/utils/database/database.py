from datetime import datetime, timedelta
import pprint
import mysql.connector
import glob
import json
import csv
from io import StringIO
import itertools
import hashlib
import os
import cryptography
from cryptography.fernet import Fernet
from math import pow

class database:

    def __init__(self, purge = False):

        # Grab information from the configuration file
        self.database       = 'db'
        self.host           = '127.0.0.1'
        self.user           = 'master'
        self.port           = 3306
        self.password       = 'master'
        self.tables         = ['institutions', 'positions', 'experiences', 'skills','feedback', 'users']
        
        # NEW IN HW 3-----------------------------------------------------------------
        self.encryption     =  {   'oneway': {'salt' : b'averysaltysailortookalongwalkoffashortbridge',
                                                 'n' : int(pow(2,5)),
                                                 'r' : 9,
                                                 'p' : 1
                                             },
                                'reversible': { 'key' : '7pK_fnSKIjZKuv_Gwc--sZEMKn2zc8VvD6zS96XcNHE='}
                                }
        #-----------------------------------------------------------------------------

    def query(self, query = "SELECT * FROM users", parameters = None):

        cnx = mysql.connector.connect(host     = self.host,
                                      user     = self.user,
                                      password = self.password,
                                      port     = self.port,
                                      database = self.database,
                                      charset  = 'latin1'
                                     )


        if parameters is not None:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query, parameters)
        else:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query)

        # Fetch one result
        row = cur.fetchall()
        cnx.commit()

        if "INSERT" in query:
            cur.execute("SELECT LAST_INSERT_ID()")
            row = cur.fetchall()
            cnx.commit()
        cur.close()
        cnx.close()
        return row
    
    
    def createTables(self, purge=False, data_path = 'flask_app/database/'):
        """ Creates tables and populates initial data. """

        create_dir = os.path.join(data_path, "create_tables")
        data_dir = os.path.join(data_path, "initial_data")

        cnx = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=self.database,
            charset='utf8mb4'
        )
        cursor = cnx.cursor()

        # Drop all tables if purge=True
        if purge:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            tables = self.query("SHOW TABLES")
            for table in tables:
                table_name = list(table.values())[0]
                cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            cnx.commit()
            print("Purged existing tables.")

        essential_tables = ["users.sql","events.sql","event_participants.sql","availability.sql"]
        executed_files = set()

        # Create essential tables first (positions before experiences)
        for table_file in essential_tables:
            sql_path = os.path.join(create_dir, table_file)
            if os.path.exists(sql_path):
                with open(sql_path, "r") as file:
                    sql_script = file.read()
                    cursor.execute(sql_script, multi=True)
                    executed_files.add(table_file)
                    print(f"Executed {table_file}")

        # Execute all other table creation scripts
        for sql_file in sorted(glob.glob(os.path.join(create_dir, "*.sql"))):
            file_name = os.path.basename(sql_file)
            if file_name not in executed_files:
                with open(sql_file, "r") as file:
                    sql_script = file.read()
                    cursor.execute(sql_script, multi=True)
                    print(f"Executed {file_name}")

        # Execute initial data population scripts
        for sql_file in sorted(glob.glob(os.path.join(data_dir, "*.sql"))):
            with open(sql_file, "r") as file:
                sql_script = file.read()
                cursor.execute(sql_script, multi=True)
                print(f"Executed {sql_file}")
        
        cnx.commit()

        # Temporarily disable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        # Insert initial data from CSV files (positions before experiences)
        for sql_file in sorted(glob.glob(os.path.join(create_dir, "*.sql"))):
            table_name = os.path.splitext(os.path.basename(sql_file))[0]  # Remove .sql extension
            csv_file = os.path.join(data_dir, f"{table_name}.csv")

            if os.path.exists(csv_file):
                with open(csv_file, 'r') as file:
                    reader = csv.reader(file)
                    columns = next(reader)  # Read the header row
                    values_placeholder = ", ".join(["%s"] * len(columns))
                    insert_query = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({values_placeholder})"

                    # Insert all rows from the CSV into the database
                    data_tuples = [tuple(None if val.strip().upper() == "NULL" or val.strip() == "" else val for val in row) for row in reader]
                    cursor.executemany(insert_query, data_tuples)
                    print(f"Inserted {len(data_tuples)} rows into {table_name} from {csv_file}")
            else:
                print(f"CSV file not found for table: {table_name}")

        # Re-enable foreign key checks after the inserts
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
        cnx.commit()
        cursor.close()
        cnx.close()
        print("Database setup complete.")

    def insertRows(self, table='table', columns=['x','y'], parameters=[['v11','v12'],['v21','v22']]):
        if not parameters:
            print("No data to insert.")
            return

        # Construct the INSERT query
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)
        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"

        cnx = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=self.database,
            charset='utf8mb4'
        )
        cursor = cnx.cursor()

        try:
            cursor.executemany(query, parameters)  # Efficient batch insert
            cnx.commit()
            print(f"Inserted {cursor.rowcount} rows into {table}.")
        except mysql.connector.Error as err:
            print(f"Error inserting rows into {table}: {err}")
        finally:
            cursor.close()
            cnx.close()


#######################################################################################
# AUTHENTICATION RELATED
#######################################################################################
    def createUser(self, email='me@email.com', password='password', role='user'):
        if role not in ['guest','owner']:
            return {'success': 0, 'error': 'Invalid role. Must be "guest" or "owner".'}
        
        encrypted_password = self.onewayEncrypt(password)
        try:
            # Check if the user already exists
            existing_user = self.query("SELECT * FROM users WHERE email = %s", (email,))
            if existing_user:
                return {'success': 0, 'error': 'User already exists.'}

            # Insert the new user into the database
            self.query("INSERT INTO users (email, password, role) VALUES (%s, %s, %s)",
                    (email, encrypted_password, role))

            return {'success': 1, 'message': 'User created successfully.'}

        except mysql.connector.Error as e:
            return {'success': 0, 'error': f'Database error: {str(e)}'}

    def authenticate(self, email='me@email.com', password='password'):
        try:
            # Encrypt the provided password using the same encryption method
            encrypted_password = self.onewayEncrypt(password)

            # Check if the user exists with the provided email and encrypted password
            user = self.query("SELECT * FROM users WHERE email = %s AND password = %s", (email, encrypted_password))
            if user:
                return {'success': 1, 'message': 'Authentication successful.'}
            else:
                return {'success': 0, 'error': 'Invalid email or password.'}

        except mysql.connector.Error as e:
            return {'success': 0, 'error': f'Database error: {str(e)}'}

    def onewayEncrypt(self, string):
        encrypted_string = hashlib.scrypt(string.encode('utf-8'),
                                          salt = self.encryption['oneway']['salt'],
                                          n    = self.encryption['oneway']['n'],
                                          r    = self.encryption['oneway']['r'],
                                          p    = self.encryption['oneway']['p']
                                          ).hex()
        return encrypted_string


    def reversibleEncrypt(self, type, message):
        fernet = Fernet(self.encryption['reversible']['key'])
        
        if type == 'encrypt':
            message = fernet.encrypt(message.encode())
        elif type == 'decrypt':
            message = fernet.decrypt(message).decode()

        return message
    
#######################################################################################
# EVENT RELATED
#######################################################################################

    def create_event(self, name, creator_email, start_date, end_date, start_time, end_time, invitees):
        try:
            cnx = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.database,
                charset='utf8mb4'
            )
            cursor = cnx.cursor(dictionary=True)

            # Insert event
            insert_query = """
                INSERT INTO events (name, creator_email, start_date, end_date, start_time, end_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (name, creator_email, start_date, end_date, start_time, end_time))
            cnx.commit()

            event_id = cursor.lastrowid
            print("Inserted event with ID:", event_id)

            # Add creator + invitees as participants
            participants = [(event_id, creator_email)] + [(event_id, email) for email in invitees]
            self.insertRows('event_participants', ['event_id', 'email'], participants)

            # Insert into event_invitees (just invitees)
            invitee_rows = [(event_id, email) for email in invitees]
            self.insertRows('event_invitees', ['event_id', 'email'], invitee_rows)

            # ========== NEW: Pre-fill Unavailable availability ==========

            availability_rows = []
            all_emails = [creator_email] + invitees

            start_time_obj = datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = datetime.strptime(end_time, "%H:%M").time()

            current_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

            while current_date <= end_date_obj:
                current_time = start_time_obj
                while current_time < end_time_obj:
                    for email in all_emails:
                        availability_rows.append((
                            event_id,
                            email,
                            current_date,
                            current_time,
                            "Unavailable"
                        ))
                    # Increment time by 30 minutes
                    dt = datetime(2000, 1, 1, current_time.hour, current_time.minute) + timedelta(minutes=30)
                    current_time = dt.time()
                current_date += timedelta(days=1)

            self.insertRows('availability', ['event_id', 'email', 'date', 'time', 'status'], availability_rows)

            # ========== END ==========

            return {'success': 1, 'event_id': event_id}
        except Exception as e:
            return {'success': 0, 'error': str(e)}
        finally:
            cursor.close()
            cnx.close()


    def get_invited_events(self, user_email):
        try:
            query = """
                SELECT e.event_id, e.name, e.creator_email, e.start_date, e.end_date
                FROM events e
                JOIN event_participants ep ON e.event_id = ep.event_id
                WHERE ep.email = %s
            """
            results = self.query(query, (user_email,))
            return results
        except Exception as e:
            print("Error fetching invited events:", e)
            return []


    def get_event_by_id(self, event_id):
        try:
            # Get the main event info
            event_query = """
                SELECT event_id, name, creator_email, start_date, end_date, start_time, end_time
                FROM events
                WHERE event_id = %s
            """
            event_result = self.query(event_query, (event_id,))
            if not event_result:
                return None
            event = event_result[0]

            # Get invitee emails
            invitee_query = """
                SELECT email FROM event_invitees WHERE event_id = %s
            """
            invitees_result = self.query(invitee_query, (event_id,))
            invitees = [row['email'] for row in invitees_result]

            # Add invitees to event dict
            event['invitees'] = invitees

            return event
        except Exception as e:
            print("Error in get_event_by_id:", e)
            return None

    def save_availability(self, event_id, email, availability_data):
        """
        Save or update a user's availability for an event.

        Parameters:
            event_id (int): The ID of the event.
            email (str): The user's email.
            availability_data (list of dict): Each dict contains:
                {
                    'date': 'YYYY-MM-DD',
                    'time': 'HH:MM:SS',
                    'status': 'Available' | 'Maybe' | 'Unavailable'
                }
        """
        try:
            cnx = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.database,
                charset='utf8mb4'
            )
            cursor = cnx.cursor()

            # Delete existing availability for this user/event (optional, for full overwrite)
            cursor.execute("DELETE FROM availability WHERE event_id = %s AND email = %s", (event_id, email))

            # Prepare insert statement
            insert_query = """
                INSERT INTO availability (event_id, email, date, time, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            for row in availability_data:
                row['time'] = datetime.strptime(row['time'], '%H:%M:%S').time()
                
            values = [(event_id, email, row['date'], row['time'], row['status']) for row in availability_data]

            # Insert all rows
            cursor.executemany(insert_query, values)
            cnx.commit()
            return {'success': 1, 'message': f'Saved {cursor.rowcount} availability entries.'}

        except Exception as e:
            return {'success': 0, 'error': str(e)}
        finally:
            cursor.close()
            cnx.close()

    def get_availability(self, event_id, email):
        """
        Retrieve a user's availability for a specific event.

        Returns:
            List of dicts, each with 'date', 'time', 'status'.
        """
        try:
            results = self.query(
                "SELECT date, time, status FROM availability WHERE event_id = %s AND email = %s",
                (event_id, email)
            )
            return results
        except Exception as e:
            print(f"Error fetching availability: {e}")
            return []
    
    def get_group_availability(self, event_id):
        query = """
            SELECT date, time, 
                SUM(status = 'Available') AS available_count,
                SUM(status = 'Maybe') AS maybe_count,
                SUM(status = 'Unavailable') AS unavailable_count
            FROM availability
            WHERE event_id = %s
            GROUP BY date, time
            ORDER BY date, time
        """
        try:
            return self.query(query, (event_id,))
        except Exception as e:
            print(f"Error fetching group availability: {e}")
            return []