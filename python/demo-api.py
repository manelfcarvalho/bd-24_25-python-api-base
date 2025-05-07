##
## =============================================
## ============== Bases de Dados ===============
## ============== LEI  2024/2025 ===============
## =============================================
## =================== Demo ====================
## =============================================
## =============================================
## === Department of Informatics Engineering ===
## =========== University of Coimbra ===========
## =============================================
##
## Authors:
##   João R. Campos <jrcampos@dei.uc.pt>
##   Nuno Antunes <nmsa@dei.uc.pt>
##   University of Coimbra


import flask 
import logging
import psycopg2
import time
import random
import datetime
import jwt
from functools import wraps

app = flask.Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'some_jwt_secret_key'

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500,
    'unauthorized': 401
}


##########################################################
## DEMO ENDPOINTS
## (the endpoints get_all_departments and add_departments serve only as examples!)
##########################################################

##
## Demo GET
##
## Obtain all departments in JSON format
##

@app.route('/departments/', methods=['GET'])
def get_all_departments():
    logger.info('GET /departments')

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT ndep, nome, local FROM dep')
        rows = cur.fetchall()

        logger.debug('GET /departments - parse')
        Results = []
        for row in rows:
            logger.debug(row)
            content = {'ndep': int(row[0]), 'nome': row[1], 'localidade': row[2]}
            Results.append(content)  # appending to the payload to be returned

        response = {'status': StatusCodes['success'], 'results': Results}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /departments - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

##
## Demo POST
##
## Add a new department in a JSON payload
##

@app.route('/departments/', methods=['POST'])
def add_departments():
    logger.info('POST /departments')
    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'POST /departments - payload: {payload}')

    # do not forget to validate every argument, e.g.,:
    if 'ndep' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'ndep value not in payload'}
        return flask.jsonify(response)

    # parameterized queries, good for security and performance
    statement = 'INSERT INTO dep (ndep, nome, local) VALUES (%s, %s, %s)'
    values = (payload['ndep'], payload['nome'], payload['localidade'])

    try:
        cur.execute(statement, values)

        # commit the transaction
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Inserted dep {payload["ndep"]}'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /departments - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        # an error occurred, rollback
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

##########################################################
## DEMO ENDPOINTS END
##########################################################







##########################################################
## DATABASE ACCESS
##########################################################

def db_connection():
    db = psycopg2.connect(
        user='aulaspl',
        password='aulaspl',
        host='127.0.0.1',
        port='5432',
        database='projeto'
    )

    return db

##########################################################
## AUTHENTICATION HELPERS
##########################################################

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = flask.request.headers.get('Authorization')
        logger.info(f'token: {token}')

        if not token:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Token is missing!', 'results': None})
        
        try:
            # Strip 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
                
            # Decode and validate token
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            # Add user info to request context for use in endpoint functions
            flask.g.person_id = data['person_id']
            flask.g.name = data['name']
            flask.g.email = data['email']
            flask.g.role = data['role']
        except jwt.ExpiredSignatureError:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Token has expired', 'results': None})
        except jwt.InvalidTokenError:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Invalid token', 'results': None})
        
        return f(*args, **kwargs)
    return decorated

##########################################################
## ENDPOINTS
##########################################################

@app.route('/persons/', methods=['POST'])
def add_person():
    logger.info('POST /persons')
    payload = flask.request.get_json()

    # validação básica dos campos obrigatórios
    required = ['name', 'age', 'gender', 'nif', 'address', 'phone', 'password']
    for field in required:
        if field not in payload:
            response = {
                'status': StatusCodes['api_error'],
                'results': f'{field} value not in payload'
            }
            return flask.jsonify(response), 400

    stmt = '''
        INSERT INTO person
            (name, age, gender, nif, email, address, phone, password)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING person_id
    '''
    vals = (
        payload['name'],
        payload['age'],
        payload['gender'],
        payload['nif'],
        payload.get('email'),
        payload['address'],
        payload['phone'],
        payload['password']
    )

    conn = db_connection()
    cur = conn.cursor()
    try:
        cur.execute(stmt, vals)
        new_id = cur.fetchone()[0]
        conn.commit()
        response = {
            'status': StatusCodes['success'],
            'results': {
                'person_id': new_id,
                'login_credentials': {
                    'email': payload.get('email'),
                    'password': payload['password']
                }
            }
        }
        return flask.jsonify(response), 201

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /persons - error: {error}')
        conn.rollback()
        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }
        return flask.jsonify(response), 500

    finally:
        if conn is not None:
            conn.close()

@app.route('/get_persons/', methods=['GET'])
def list_persons():
    logger.info('GET /persons')

    stmt = '''
        SELECT
            person_id,
            name,
            age,
            gender,
            nif,
            email,
            address,
            phone
        FROM person
        ORDER BY person_id
    '''

    conn = db_connection()
    cur = conn.cursor()
    try:
        cur.execute(stmt)
        rows = cur.fetchall()

        persons = []
        for person_id, name, age, gender, nif, email, address, phone in rows:
            persons.append({
                'person_id': person_id,
                'name': name,
                'age': age,
                'gender': gender,
                'nif': nif,
                'email': email,
                'address': address,
                'phone': phone
            })

        return flask.jsonify({
            'status': StatusCodes['success'],
            'results': persons
        }), 200

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /persons - error: {error}')
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }), 500

    finally:
        if conn is not None:
            conn.close()


@app.route('/dbproj/user', methods=['PUT'])
def login_user():
    data = flask.request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Email and password are required', 'results': None})

    # Connect to database
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Query para verificar credenciais usando a tabela person
        stmt = '''
            SELECT p.person_id, p.name, p.email
            FROM person p
            WHERE p.email = %s AND p.password = %s
        '''
        cur.execute(stmt, (email, password))
        user = cur.fetchone()
        
        if user is None:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Invalid email or password', 'results': None})
        
        person_id, name, email = user
        
        # Verificar tipo de usuário
        role = 'unknown'
        
        # Verificar se é estudante
        cur.execute('SELECT person_person_id FROM student WHERE person_person_id = %s', (person_id,))
        is_student = cur.fetchone() is not None
        
        # Verificar se é instructor
        cur.execute('SELECT worker_person_person_id FROM instructor WHERE worker_person_person_id = %s', (person_id,))
        is_instructor = cur.fetchone() is not None
        
        # Verificar se é staff
        cur.execute('SELECT worker_person_person_id FROM staff WHERE worker_person_person_id = %s', (person_id,))
        is_staff = cur.fetchone() is not None
        
        # Determinar role
        if is_student:
            role = 'student'
        elif is_instructor:
            role = 'instructor'
        elif is_staff:
            role = 'staff'
        
        # Gerar token JWT com informações do usuário
        token_payload = {
            'person_id': person_id,
            'name': name,
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)  # Token expira em 24 horas
        }
        
        token = jwt.encode(token_payload, app.config['JWT_SECRET_KEY'], algorithm="HS256")
        
        response = {'status': StatusCodes['success'], 'errors': None, 'results': token}
        return flask.jsonify(response)
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'PUT /dbproj/user - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
        return flask.jsonify(response)
        
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/register/student', methods=['POST'])
@token_required
def register_student():
    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})
    
    resultUserId = random.randint(1, 200) # TODO

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultUserId}
    return flask.jsonify(response)

@app.route('/dbproj/register/staff', methods=['POST'])
@token_required
def register_staff():
    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})
    
    resultUserId = random.randint(1, 200) # TODO

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultUserId}
    return flask.jsonify(response)

@app.route('/dbproj/register/instructor', methods=['POST'])
@token_required
def register_instructor():
    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})
    
    resultUserId = random.randint(1, 200) # TODO

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultUserId}
    return flask.jsonify(response)

@app.route('/dbproj/enroll_degree/<degree_id>', methods=['POST'])
@token_required
def enroll_degree(degree_id):
    data = flask.request.get_json()
    student_id = data.get('student_id')
    date = data.get('date')

    if not student_id or not date:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student ID and date are required', 'results': None})
    
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/enroll_activity/<activity_id>', methods=['POST'])
@token_required
def enroll_activity(activity_id):
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/enroll_course_edition/<course_edition_id>', methods=['POST'])
@token_required
def enroll_course_edition(course_edition_id):
    data = flask.request.get_json()
    classes = data.get('classes', [])

    if not classes:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'At least one class ID is required', 'results': None})
    
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/submit_grades/<course_edition_id>', methods=['POST'])
@token_required
def submit_grades(course_edition_id):
    data = flask.request.get_json()
    period = data.get('period')
    grades = data.get('grades', [])

    if not period or not grades:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Evaluation period and grades are required', 'results': None})
    
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/student_details/<student_id>', methods=['GET'])
@token_required
def student_details(student_id):

    resultStudentDetails = [ # TODO
        {
            'course_edition_id': random.randint(1, 200),
            'course_name': "some course",
            'course_edition_year': 2024,
            'grade': 12
        },
        {
            'course_edition_id': random.randint(1, 200),
            'course_name': "another course",
            'course_edition_year': 2025,
            'grade': 17
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultStudentDetails}
    return flask.jsonify(response)

@app.route('/dbproj/degree_details/<degree_id>', methods=['GET'])
@token_required
def degree_details(degree_id):

    resultDegreeDetails = [ # TODO
        {
            'course_id': random.randint(1, 200),
            'course_name': "some coure",
            'course_edition_id': random.randint(1, 200),
            'course_edition_year': 2023,
            'capacity': 30,
            'enrolled_count': 27,
            'approved_count': 20,
            'coordinator_id': random.randint(1, 200),
            'instructors': [random.randint(1, 200), random.randint(1, 200)]
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultDegreeDetails}
    return flask.jsonify(response)

@app.route('/dbproj/top3', methods=['GET'])
@token_required
def top3_students():

    resultTop3 = [ # TODO
        {
            'student_name': "John Doe",
            'average_grade': 15.1,
            'grades': [
                {
                    'course_edition_id': random.randint(1, 200),
                    'course_edition_name': "some course",
                    'grade': 15.1,
                    'date': datetime.datetime(2024, 5, 12)
                }
            ],
            'activities': [random.randint(1, 200), random.randint(1, 200)]
        },
        {
            'student_name': "Jane Doe",
            'average_grade': 16.3,
            'grades': [
                {
                    'course_edition_id': random.randint(1, 200),
                    'course_edition_name': "another course",
                    'grade': 15.1,
                    'date': datetime.datetime(2023, 5, 11)
                }
            ],
            'activities': [random.randint(1, 200)]
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultTop3}
    return flask.jsonify(response)

@app.route('/dbproj/top_by_district', methods=['GET'])
@token_required
def top_by_district():

    resultTopByDistrict = [ # TODO
        {
            'student_id': random.randint(1, 200),
            'district': "Coimbra",
            'average_grade': 15.2
        },
        {
            'student_id': random.randint(1, 200),
            'district': "Coimbra",
            'average_grade': 13.6
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultTopByDistrict}
    return flask.jsonify(response)

@app.route('/dbproj/report', methods=['GET'])
@token_required
def monthly_report():

    resultReport = [ # TODO
        {
            'month': "month_0",
            'course_edition_id': random.randint(1, 200),
            'course_edition_name': "Some course",
            'approved': 20,
            'evaluated': 23
        },
        {
            'month': "month_1",
            'course_edition_id': random.randint(1, 200),
            'course_edition_name': "Another course",
            'approved': 200,
            'evaluated': 123
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultReport}
    return flask.jsonify(response)

@app.route('/dbproj/auth-test', methods=['GET'])
@token_required
def auth_test():
    """Test endpoint that demonstrates how to access the authenticated user information"""
    # Access user information from the token (stored in flask.g)
    user_info = {
        'person_id': flask.g.person_id,
        'name': flask.g.name,
        'email': flask.g.email,
        'role': flask.g.role
    }
    
    response = {
        'status': StatusCodes['success'], 
        'errors': None, 
        'results': {
            'message': 'Authentication successful',
            'user_info': user_info
        }
    }
    return flask.jsonify(response)

@app.route('/dbproj/delete_details/<student_id>', methods=['DELETE'])
@token_required
def delete_student(student_id):
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/set-role/student/<int:person_id>', methods=['POST'])
@token_required
def set_student_role(person_id):
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a person existe
        cur.execute('SELECT person_id FROM person WHERE person_id = %s', (person_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Person not found',
                'results': None
            }), 404

        # Inserir na tabela student
        cur.execute('INSERT INTO student (person_person_id) VALUES (%s)', (person_id,))
        conn.commit()
        
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': f'Person {person_id} is now a student'
        })

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error setting student role: {error}')
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500

    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/set-role/instructor/<int:person_id>', methods=['POST'])
@token_required
def set_instructor_role(person_id):
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a person existe
        cur.execute('SELECT person_id FROM person WHERE person_id = %s', (person_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Person not found',
                'results': None
            }), 404

        # Primeiro inserir na tabela worker
        cur.execute('''
            INSERT INTO worker (person_person_id, salary, start_date)
            VALUES (%s, %s, CURRENT_DATE)
            RETURNING worker_id
        ''', (person_id, 0.0))  # Salary inicial 0, pode ser atualizado depois
        worker_id = cur.fetchone()[0]

        # Depois inserir na tabela instructor
        cur.execute('INSERT INTO instructor (worker_person_person_id) VALUES (%s)', (person_id,))
        conn.commit()
        
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': f'Person {person_id} is now an instructor'
        })

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error setting instructor role: {error}')
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500

    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/set-role/staff/<int:person_id>', methods=['POST'])
@token_required
def set_staff_role(person_id):
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a person existe
        cur.execute('SELECT person_id FROM person WHERE person_id = %s', (person_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Person not found',
                'results': None
            }), 404

        # Primeiro inserir na tabela worker
        cur.execute('''
            INSERT INTO worker (person_person_id, salary, start_date)
            VALUES (%s, %s, CURRENT_DATE)
            RETURNING worker_id
        ''', (person_id, 0.0))  # Salary inicial 0, pode ser atualizado depois
        worker_id = cur.fetchone()[0]

        # Depois inserir na tabela staff
        cur.execute('INSERT INTO staff (worker_person_person_id) VALUES (%s)', (person_id,))
        conn.commit()
        
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': f'Person {person_id} is now a staff member'
        })

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error setting staff role: {error}')
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500

    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    # set up logging
    logging.basicConfig(filename='log_file.log')
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:  %(message)s', '%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    host = '127.0.0.1'
    port = 8080
    app.run(host=host, debug=True, threaded=True, port=port)
    logger.info(f'API stubs online: http://{host}:{port}')
