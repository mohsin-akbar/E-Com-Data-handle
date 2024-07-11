from flask import Flask, render_template, request,redirect, url_for
import oracledb

app = Flask(__name__)

# List of allowed tables
ALLOWED_TABLES = [
    'CONTACTS', 'COUNTRIES', 'CUSTOMERS', 'EMPLOYEES', 'INVENTORIES',
    'LOCATIONS', 'ORDER_ITEMS', 'ORDERS', 'PRODUCT_CATEGORIES', 'PRODUCTS',
    'REGIONS', 'WAREHOUSES'
]

def get_db_connection():
    # Update these values with your actual database credentials
    dsn = oracledb.makedsn("localhost", "1521", service_name="xepdb1")
    conn = oracledb.connect(user=u"dbuser", password="dbuser", dsn=dsn)
    return conn

@app.route('/')
def index():
    return render_template('index1.html', tables=ALLOWED_TABLES)

@app.route('/show_table', methods=['GET','POST'])
def show_table():
    if request.method == 'POST':
        selected_table = request.form.get('table_name')
    else:  # GET request
        selected_table = request.args.get('table_name')
    print(f"Selected table: {selected_table}")# Debugging line
    if selected_table not in ALLOWED_TABLES:
        print("Invalid table selection")  # Debugging line
        return "Invalid table selection", 400
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the data from the selected table
    cursor.execute(f"SELECT * FROM {selected_table}")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('table1.html', columns=columns, rows=rows, table_name=selected_table)

#updating file 


@app.route('/edit_record/<table_name>/<record_id>', methods=['GET', 'POST'])
def edit_record(table_name, record_id):
    print(f"table name came:{table_name} and recordid {record_id}")
    if table_name not in ALLOWED_TABLES:
        return "Invalid table selection", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the primary key column name for the table
    cursor.execute("""
        SELECT cols.column_name
        FROM all_constraints cons, all_cons_columns cols
        WHERE cols.table_name = :table_name
        AND cons.constraint_type = 'P'
        AND cons.constraint_name = cols.constraint_name
        AND cons.owner = cols.owner
    """, [table_name.upper()])
    primary_key_column = cursor.fetchone()[0]

    if request.method == 'POST':
        print(f"post runs {table_name} and recordid {record_id}")
        # Extract updated data from the form
        updated_data = {col: request.form[col] for col in request.form}# i ndeed to send table name and id from edit form
        print(f"updated data {updated_data}")
        # Validate foreign key values
        for column, value in updated_data.items():
            cursor.execute("""
                SELECT acc.constraint_name, acc.position, acc.table_name, acc.column_name, ac.constraint_type
                FROM all_cons_columns acc
                JOIN all_constraints ac ON acc.constraint_name = ac.constraint_name
                WHERE ac.constraint_type = 'R'
                AND acc.table_name = :table_name
                AND acc.column_name = :column_name
            """, [table_name.upper(), column.upper()])
            fk_constraint = cursor.fetchone()
            if fk_constraint:
                parent_table = fk_constraint[2]
                cursor.execute(f"SELECT COUNT(*) FROM {parent_table} WHERE {column} = :value", [value])
                if cursor.fetchone()[0] == 0:
                    return f"Invalid value for foreign key column {column}", 400

        # Check for unique constraint violation
        for column, value in updated_data.items():
            cursor.execute(f"""
                SELECT constraint_name
                FROM all_constraints
                WHERE constraint_type = 'U'
                AND table_name = :table_name
                AND constraint_name IN (
                    SELECT constraint_name
                    FROM all_cons_columns
                    WHERE column_name = :column_name
                )
            """, [table_name.upper(), column.upper()])
            unique_constraint = cursor.fetchone()
            if unique_constraint:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column} = :value AND {primary_key_column} != :id", {'value': value, 'id': record_id})
                if cursor.fetchone()[0] > 0:
                    return f"Unique constraint violation on column {column}", 400
                # Function to construct the set clause
        def construct_set_clause(updated_data):
            set_clauses = []
            for col in updated_data.keys():
                if col == 'ORDER_DATE' or col=='HIRE_DATE':
                    set_clauses.append(f"{col} = TO_DATE(:{col}, 'YYYY-MM-DD HH24:MI:SS')")
                else:
                    set_clauses.append(f"{col} = :{col}")
            return ", ".join(set_clauses)
                
        set_clause = construct_set_clause(updated_data)
        query = f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE {primary_key_column} = :id
        """
        print(f"query:=> {query}")
        updated_data['id'] = record_id
        print(f"post runs {updated_data} before try")

        try:
            cursor.execute(query, updated_data)
            print(f"post runs {updated_data} in try")
            conn.commit()
        except oracledb.IntegrityError as e:
            return f"Integrity error: {e}", 400


        cursor.close()
        conn.close()
        print(f"table_name: {table_name} id :{record_id}")
        return redirect(url_for('show_table', table_name=table_name))

    cursor.execute(f"SELECT * FROM {table_name} WHERE {primary_key_column} = :id", [record_id])
    record = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    return render_template('edit_record.html', columns=columns, record=record, table_name=table_name, record_id=record_id,zip=zip)



if __name__ == '__main__':
    app.run(debug=True)
