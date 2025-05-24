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

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Inserir na tabela person
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

        cur.execute(stmt, vals)
        person_id = cur.fetchone()[0]

        conn.commit()
        response = {
            'status': StatusCodes['success'],
            'results': {
                'person_id': person_id
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
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can register new students',
            'results': None
        }), 403

    data = flask.request.get_json()
    person_id = data.get('person_id')
    enrolment_date = datetime.date.today()  # Use today's date by default
    mean = data.get('mean', 0.0)
    major_id = data.get('major_id')  # Opcional

    if not person_id:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'person_id is required',
            'results': None
        })
    
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a pessoa existe
        cur.execute('SELECT person_id FROM person WHERE person_id = %s', (person_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Person not found',
                'results': None
            })
            
        # Verificar se já é um estudante
        cur.execute('SELECT person_person_id FROM student WHERE person_person_id = %s', (person_id,))
        if cur.fetchone() is not None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'This person is already a student',
                'results': None
            })
        
        # Inserir na tabela student com os atributos específicos
        cur.execute('''
            INSERT INTO student (person_person_id, enrolment_date, mean)
            VALUES (%s, %s, %s)
        ''', (person_id, enrolment_date, mean))
        
        # Se foi especificado um major, criar a matrícula
        if major_id:
            # Criar conta de taxas
            cur.execute('INSERT INTO fees_account (values_acumulate) VALUES (0) RETURNING fees_account_id')
            fees_account_id = cur.fetchone()[0]
            
            # Matricular no major
            cur.execute('''
                INSERT INTO major_info (student_person_person_id, major_major_id, fees, status, fees_account_fees_account_id)
                VALUES (%s, %s, %s, 'Active', %s)
            ''', (person_id, major_id, 5000.00, fees_account_id))
        
        conn.commit()
        response = {
            'status': StatusCodes['success'], 
            'errors': None, 
            'results': {
                'person_id': person_id,
                'enrolment_date': enrolment_date.strftime('%Y-%m-%d'),
                'mean': mean,
                'major_id': major_id
            }
        }
        return flask.jsonify(response)
        
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        })
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/register/staff', methods=['POST'])
@token_required
def register_staff():
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can register new staff',
            'results': None
        }), 403

    data = flask.request.get_json()
    person_id = data.get('person_id')
    salary = data.get('salary', 0.0)
    started_working = datetime.date.today()  # Use today's date by default

    if not person_id:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'person_id is required',
            'results': None
        })
    
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a pessoa existe
        cur.execute('SELECT person_id FROM person WHERE person_id = %s', (person_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Person not found',
                'results': None
            })
            
        # Verificar se já é um staff
        cur.execute('SELECT worker_person_person_id FROM staff WHERE worker_person_person_id = %s', (person_id,))
        if cur.fetchone() is not None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'This person is already a staff member',
                'results': None
            })
        
        # Inserir na tabela worker com os atributos específicos
        cur.execute('''
            INSERT INTO worker (person_person_id, salary, started_working)
            VALUES (%s, %s, %s)
        ''', (person_id, salary, started_working))
        
        # Inserir na tabela staff
        cur.execute('''
            INSERT INTO staff (worker_person_person_id)
            VALUES (%s)
        ''', (person_id,))
        
        conn.commit()
        response = {
            'status': StatusCodes['success'], 
            'errors': None, 
            'results': {
                'person_id': person_id,
                'salary': salary,
                'started_working': started_working.strftime('%Y-%m-%d')
            }
        }
        return flask.jsonify(response)
        
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        })
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/register/instructor', methods=['POST'])
@token_required
def register_instructor():
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can register new instructors',
            'results': None
        }), 403

    data = flask.request.get_json()
    person_id = data.get('person_id')
    salary = data.get('salary', 0.0)
    started_working = data.get('started_working', datetime.date.today())
    major = data.get('major', 'General')
    department_id = data.get('department_id')

    if not person_id:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'person_id is required',
            'results': None
        })
    
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a pessoa existe
        cur.execute('SELECT person_id FROM person WHERE person_id = %s', (person_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Person not found',
                'results': None
            })
            
        # Verificar se já é um instructor
        cur.execute('SELECT worker_person_person_id FROM instructor WHERE worker_person_person_id = %s', (person_id,))
        if cur.fetchone() is not None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'This person is already an instructor',
                'results': None
            })
        
        # Se não foi fornecido department_id, pegar o primeiro disponível
        if not department_id:
            cur.execute('SELECT department_id FROM department LIMIT 1')
            result = cur.fetchone()
            if result:
                department_id = result[0]
            else:
                return flask.jsonify({
                    'status': StatusCodes['api_error'],
                    'errors': 'No department available',
                    'results': None
                })
        
        # Inserir na tabela worker com os atributos específicos
        cur.execute('''
            INSERT INTO worker (person_person_id, salary, started_working)
            VALUES (%s, %s, %s)
        ''', (person_id, salary, started_working))
        
        # Inserir na tabela instructor com os atributos específicos
        cur.execute('''
            INSERT INTO instructor (worker_person_person_id, major, department_department_id)
            VALUES (%s, %s, %s)
        ''', (person_id, major, department_id))
        
        conn.commit()
        response = {
            'status': StatusCodes['success'], 
            'errors': None, 
            'results': {
                'person_id': person_id,
                'salary': salary,
                'started_working': started_working.strftime('%Y-%m-%d'),
                'major': major,
                'department_id': department_id
            }
        }
        return flask.jsonify(response)
        
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        })
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/enroll_degree/<int:major_id>', methods=['POST'])
@token_required
def enroll_degree(major_id):
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can enroll students in majors',
            'results': None
        }), 403

    data = flask.request.get_json()
    student_id = data.get('student_id')

    if not student_id:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'student_id is required',
            'results': None
        }), 400

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se o estudante existe
        cur.execute('SELECT person_person_id FROM student WHERE person_person_id = %s', (student_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student not found',
                'results': None
            }), 404

        # Verificar se o major existe
        cur.execute('SELECT major_name FROM major WHERE major_id = %s', (major_id,))
        major = cur.fetchone()
        if not major:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Major not found',
                'results': None
            }), 404

        # Verificar se o estudante já tem algum registro em major_info
        cur.execute('''
            SELECT mi.status, m.major_name, mi.fees_account_fees_account_id
            FROM major_info mi
            JOIN major m ON mi.major_major_id = m.major_id
            WHERE mi.student_person_person_id = %s
        ''', (student_id,))
        
        existing_record = cur.fetchone()
        
        if existing_record:
            if existing_record[0] == 'Active':
                return flask.jsonify({
                    'status': StatusCodes['api_error'],
                    'errors': f'Student is already enrolled in major: {existing_record[1]}. Must unenroll first.',
                    'results': None
                }), 400
            else:
                # Se existe um registro inativo, atualizar para o novo major
                cur.execute('''
                    UPDATE major_info 
                    SET major_major_id = %s, 
                        status = 'Active',
                        fees = 5000.00
                    WHERE student_person_person_id = %s
                    RETURNING fees_account_fees_account_id
                ''', (major_id, student_id))
                fees_account_id = cur.fetchone()[0]
        else:
            # Criar nova conta de taxas
            cur.execute('INSERT INTO fees_account (values_acumulate) VALUES (0) RETURNING fees_account_id')
            fees_account_id = cur.fetchone()[0]

            # Matricular o estudante no novo major
            cur.execute('''
                INSERT INTO major_info (student_person_person_id, major_major_id, fees, status, fees_account_fees_account_id)
                VALUES (%s, %s, %s, 'Active', %s)
            ''', (student_id, major_id, 5000.00, fees_account_id))

        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'message': f'Successfully enrolled student {student_id} in major: {major[0]}',
                'student_id': student_id,
                'major_id': major_id,
                'major_name': major[0],
                'fees_account_id': fees_account_id
            }
        })

    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        })
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/unenroll_degree', methods=['POST'])
@token_required
def unenroll_degree():
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can unenroll students from majors',
            'results': None
        }), 403

    data = flask.request.get_json()
    student_id = data.get('student_id')

    if not student_id:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'student_id is required',
            'results': None
        }), 400

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se o estudante existe
        cur.execute('SELECT person_person_id FROM student WHERE person_person_id = %s', (student_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student not found',
                'results': None
            }), 404

        # Verificar se o estudante está matriculado em algum major
        cur.execute('''
            SELECT m.major_name, mi.major_major_id
            FROM major_info mi
            JOIN major m ON mi.major_major_id = m.major_id
            WHERE mi.student_person_person_id = %s AND mi.status = 'Active'
        ''', (student_id,))
        
        current_major = cur.fetchone()
        if not current_major:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student is not enrolled in any major',
                'results': None
            }), 400

        # Inativar a matrícula atual
        cur.execute('''
            UPDATE major_info 
            SET status = 'Inactive'
            WHERE student_person_person_id = %s AND major_major_id = %s AND status = 'Active'
            RETURNING major_major_id
        ''', (student_id, current_major[1]))
        
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Failed to update major status. The student might already be inactive.',
                'results': None
            }), 400

        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'message': f'Successfully unenrolled student {student_id} from major: {current_major[0]}',
                'student_id': student_id,
                'major_name': current_major[0],
                'major_id': current_major[1]
            }
        })

    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/enroll_activity/<activity_id>', methods=['POST'])
@token_required
def enroll_activity(activity_id):
    # Verificar se o usuário é estudante
    if flask.g.role != 'student':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only students can enroll in activities',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a atividade existe
        cur.execute('SELECT activity_id, name FROM extraactivities WHERE activity_id = %s', (activity_id,))
        activity = cur.fetchone()
        if not activity:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Activity not found',
                'results': None
            }), 404

        # Verificar se o estudante já está inscrito nesta atividade
        cur.execute('''
            SELECT extraactivities_activity_id 
            FROM extraactivities_student 
            WHERE student_person_person_id = %s AND extraactivities_activity_id = %s
        ''', (flask.g.person_id, activity_id))
        
        if cur.fetchone():
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student is already enrolled in this activity',
                'results': None
            }), 400

        # Criar uma nova conta de taxas para a atividade
        cur.execute('INSERT INTO fees_account (values_acumulate) VALUES (0) RETURNING fees_account_id')
        fees_account_id = cur.fetchone()[0]

        # Inscrever o estudante na atividade
        cur.execute('''
            INSERT INTO extraactivities_student (student_person_person_id, extraactivities_activity_id)
            VALUES (%s, %s)
        ''', (flask.g.person_id, activity_id))

        # Criar registro de taxas para a atividade (assumindo uma taxa padrão de 50)
        cur.execute('''
            INSERT INTO extraactivities_fees 
            (student_person_person_id, extraactivities_activity_id, fees, status, fees_account_fees_account_id)
            VALUES (%s, %s, %s, %s, %s)
        ''', (flask.g.person_id, activity_id, 50.0, 'Pending', fees_account_id))

        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'message': f'Successfully enrolled in activity: {activity[1]}',
                'activity_id': activity[0],
                'activity_name': activity[1],
                'fees_account_id': fees_account_id,
                'fees': 50.0,
                'status': 'Pending'
            }
        })

    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        })
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/enroll_course_edition/<course_edition_id>', methods=['POST'])
@token_required
def enroll_course_edition(course_edition_id):
    # Verificar se o usuário é estudante
    if flask.g.role != 'student':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only students can enroll in course editions',
            'results': None
        }), 403

    data = flask.request.get_json()
    classes = data.get('classes', [])

    if not classes:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'At least one class ID is required',
            'results': None
        }), 400

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a edição do curso existe
        cur.execute('''
            SELECT e.edition_id, c.course_name, e.capacity, c.course_id
            FROM edition e
            JOIN course c ON e.course_course_id = c.course_id
            WHERE e.edition_id = %s
        ''', (course_edition_id,))
        
        edition = cur.fetchone()
        if not edition:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Course edition not found',
                'results': None
            }), 404

        # Verificar se o estudante já está inscrito neste curso
        cur.execute('''
            SELECT course_course_id 
            FROM student_course 
            WHERE student_person_person_id = %s AND course_course_id = %s
        ''', (flask.g.person_id, edition[3]))  # edition[3] é o course_id
        
        if cur.fetchone():
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student is already enrolled in this course',
                'results': None
            }), 400

        # Verificar se há vagas disponíveis
        cur.execute('''
            SELECT COUNT(*) 
            FROM student_course 
            WHERE course_course_id = %s
        ''', (edition[3],))
        
        current_enrollments = cur.fetchone()[0]
        if current_enrollments >= edition[2]:  # edition[2] é a capacidade
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Course edition is at maximum capacity',
                'results': None
            }), 400

        # Verificar se todas as classes existem e pertencem a esta edição
        class_placeholders = ','.join(['%s'] * len(classes))
        cur.execute(f'''
            SELECT class_id 
            FROM class 
            WHERE class_id IN ({class_placeholders})
        ''', classes)
        
        valid_classes = {r[0] for r in cur.fetchall()}
        invalid_classes = [cid for cid in classes if cid not in valid_classes]
        if invalid_classes:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': f'Invalid class IDs: {invalid_classes}',
                'results': None
            }), 400

        # Inscrever o estudante no curso
        cur.execute('''
            INSERT INTO student_course (student_person_person_id, course_course_id)
            VALUES (%s, %s)
        ''', (flask.g.person_id, edition[3]))

        # Criar registros de presença para cada classe
        for class_id in classes:
            cur.execute('''
                INSERT INTO attendance (student_person_person_id, class_class_id, present)
                VALUES (%s, %s, false)
            ''', (flask.g.person_id, class_id))

        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'message': f'Successfully enrolled in course: {edition[1]}',
                'course_edition_id': edition[0],
                'course_name': edition[1],
                'course_id': edition[3],
                'enrolled_classes': list(classes)
            }
        })

    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        })
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/submit_grades/<course_edition_id>', methods=['POST'])
@token_required
def submit_grades(course_edition_id):
    # Verificar se o usuário é instrutor
    if flask.g.role != 'instructor':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only instructors can submit grades',
            'results': None
        }), 403

    data = flask.request.get_json()
    period = data.get('period')
    grades = data.get('grades', [])

    if not period or not grades:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Evaluation period and grades are required',
            'results': None
        }), 400

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se a edição do curso existe e se o instrutor é o coordenador
        cur.execute('''
            SELECT e.edition_id, c.course_name, e.exam_exam_id
            FROM edition e
            JOIN course c ON e.course_course_id = c.course_id
            WHERE e.edition_id = %s AND e.coordinator_instructor_worker_person_person_id = %s
        ''', (course_edition_id, flask.g.person_id))
        
        edition = cur.fetchone()
        if not edition:
            return flask.jsonify({
                'status': StatusCodes['unauthorized'],
                'errors': 'You are not the coordinator of this course edition',
                'results': None
            }), 403

        # Verificar se todos os estudantes estão matriculados nesta edição
        student_ids = [grade[0] for grade in grades]
        placeholders = ','.join(['%s'] * len(student_ids))
        
        cur.execute(f'''
            SELECT student_person_person_id
            FROM student_course sc
            JOIN edition e ON sc.course_course_id = e.course_course_id
            WHERE e.edition_id = %s AND sc.student_person_person_id IN ({placeholders})
        ''', (course_edition_id, *student_ids))
        
        enrolled_students = {r[0] for r in cur.fetchall()}
        invalid_students = [sid for sid in student_ids if sid not in enrolled_students]
        
        if invalid_students:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': f'Students with IDs {invalid_students} are not enrolled in this course edition',
                'results': None
            }), 400

        # Validar as notas (entre 0 e 20)
        invalid_grades = [(sid, grade) for sid, grade in grades if not 0 <= grade <= 20]
        if invalid_grades:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': f'Invalid grades (must be between 0 and 20): {invalid_grades}',
                'results': None
            }), 400

        # Inserir ou atualizar as notas
        results = []
        for student_id, grade in grades:
            # Verificar se já existe uma nota para este estudante neste exame
            cur.execute('''
                SELECT result_id
                FROM result
                WHERE student_person_person_id = %s AND exam_exam_id = %s
            ''', (student_id, edition[2]))  # edition[2] é o exam_exam_id
            
            existing_result = cur.fetchone()
            
            if existing_result:
                # Atualizar nota existente
                cur.execute('''
                    UPDATE result
                    SET score = %s
                    WHERE result_id = %s
                    RETURNING result_id
                ''', (grade, existing_result[0]))
                result_id = existing_result[0]
                action = 'updated'
            else:
                # Primeiro garantir que o estudante está inscrito no exame
                cur.execute('''
                    INSERT INTO exam_student (exam_exam_id, student_person_person_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                ''', (edition[2], student_id))
                
                # Inserir nova nota
                cur.execute('''
                    INSERT INTO result (student_person_person_id, exam_exam_id, score)
                    VALUES (%s, %s, %s)
                    RETURNING result_id
                ''', (student_id, edition[2], grade))
                result_id = cur.fetchone()[0]
                action = 'inserted'
            
            results.append({
                'student_id': student_id,
                'grade': grade,
                'result_id': result_id,
                'action': action
            })

        # Atualizar a média do estudante
        for student_id, _ in grades:
            cur.execute('''
                UPDATE student
                SET mean = (
                    SELECT AVG(score)
                    FROM result
                    WHERE student_person_person_id = %s
                )
                WHERE person_person_id = %s
            ''', (student_id, student_id))

        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'message': f'Successfully submitted grades for {edition[1]}',
                'course_edition_id': edition[0],
                'course_name': edition[1],
                'exam_id': edition[2],
                'period': period,
                'grades': results
            }
        })

    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        })
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/student_details/<int:student_id>', methods=['GET'])
@token_required
def student_course_details(student_id):
    # Verificar se o usuário é staff ou o próprio estudante
    if flask.g.role != 'staff' and str(flask.g.person_id) != str(student_id):
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff or the student themselves can access this information',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se o estudante existe
        cur.execute('SELECT person_person_id FROM student WHERE person_person_id = %s', (student_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student not found',
                'results': None
            }), 404
            
        # Buscar todos os cursos em que o estudante está matriculado
        cur.execute('''
            SELECT 
                e.edition_id as course_edition_id,
                c.course_name as course_name
            FROM student_course sc
            JOIN course c ON sc.course_course_id = c.course_id
            JOIN edition e ON c.course_id = e.course_course_id
            WHERE sc.student_person_person_id = %s
            ORDER BY e.edition_id DESC, c.course_name
        ''', (student_id,))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'course_edition_id': row[0],
                'course_name': row[1],
                'course_edition_year': None,  # Não temos o ano na tabela
                'grade': None  # Como não temos acesso direto às notas
            })
        
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': results
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error getting student details: {error}')
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500
        
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/degree_details/<degree_id>', methods=['GET'])
@token_required
def degree_details(degree_id):
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can access this information',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Uma única query para obter todos os detalhes necessários
        cur.execute('''
            SELECT 
                c.course_id,
                c.course_name,
                e.edition_id as course_edition_id,
                e.capacity as course_edition_year,
                e.capacity,
                (SELECT COUNT(DISTINCT sc.student_person_person_id)
                 FROM student_course sc
                 WHERE sc.course_course_id = c.course_id) as enrolled_count,
                (SELECT COUNT(DISTINCT r.student_person_person_id)
                 FROM result r
                 JOIN exam ex ON r.exam_exam_id = ex.exam_id
                 WHERE r.score >= 9.5 AND ex.exam_id = e.exam_exam_id) as approved_count,
                e.coordinator_instructor_worker_person_person_id as coordinator_id,
                ARRAY(
                    SELECT DISTINCT i.worker_person_person_id
                    FROM instructor i
                    JOIN assistant a ON i.worker_person_person_id = a.instructor_worker_person_person_id
                    JOIN assistant_class ac ON a.instructor_worker_person_person_id = ac.assistant_instructor_worker_person_person_id
                    JOIN class cl ON ac.class_class_id = cl.class_id
                    WHERE cl.class_id = e.class_class_id
                ) as instructors
            FROM course c
            JOIN edition e ON c.course_id = e.course_course_id
            WHERE c.course_id = %s
            ORDER BY e.edition_id DESC
        ''', (degree_id,))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'course_id': row[0],
                'course_name': row[1],
                'course_edition_id': row[2],
                'course_edition_year': row[3],
                'capacity': row[4],
                'enrolled_count': row[5] or 0,
                'approved_count': row[6] or 0,
                'coordinator_id': row[7],
                'instructors': row[8] if row[8] else []
            })
            
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': results
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error getting degree details: {error}')
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500
        
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/top3', methods=['GET'])
@token_required
def top3_students():
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can access this information',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Query única para obter top 3 estudantes do ano acadêmico atual
        cur.execute('''
            WITH top_students AS (
                SELECT 
                    p.name as student_name,
                    AVG(r.score) as average_grade,
                    ARRAY_AGG(DISTINCT ea.activity_id) as activities,
                    ROW_NUMBER() OVER (ORDER BY AVG(r.score) DESC) as rank
                FROM student s
                JOIN person p ON s.person_person_id = p.person_id
                JOIN result r ON s.person_person_id = r.student_person_person_id
                JOIN exam ex ON r.exam_exam_id = ex.exam_id
                JOIN edition e ON ex.exam_id = e.exam_exam_id
                LEFT JOIN extraactivities_student eas ON s.person_person_id = eas.student_person_person_id
                LEFT JOIN extraactivities ea ON eas.extraactivities_activity_id = ea.activity_id
                WHERE EXTRACT(YEAR FROM ex.data) = 
                    CASE 
                        WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 THEN EXTRACT(YEAR FROM CURRENT_DATE)
                        ELSE EXTRACT(YEAR FROM CURRENT_DATE) - 1
                    END
                GROUP BY p.name
                HAVING COUNT(DISTINCT e.edition_id) > 0
            )
            SELECT 
                ts.student_name,
                ROUND(ts.average_grade::numeric, 2) as average_grade,
                json_agg(
                    json_build_object(
                        'course_edition_id', e.edition_id,
                        'course_name', c.course_name,
                        'score', r.score,
                        'exam_date', ex.data
                    ) ORDER BY ex.data DESC
                ) as grades,
                ts.activities
            FROM top_students ts
            JOIN result r ON r.student_person_person_id = (
                SELECT s2.person_person_id 
                FROM student s2 
                JOIN person p2 ON s2.person_person_id = p2.person_id 
                WHERE p2.name = ts.student_name
                LIMIT 1
            )
            JOIN exam ex ON r.exam_exam_id = ex.exam_id
            JOIN edition e ON ex.exam_id = e.exam_exam_id
            JOIN course c ON e.course_course_id = c.course_id
            WHERE ts.rank <= 3
            GROUP BY ts.student_name, ts.average_grade, ts.activities, ts.rank
            ORDER BY ts.average_grade DESC
        ''')
        
        results = []
        for row in cur.fetchall():
            student_name, average_grade, grades, activities = row
            results.append({
                    'student_name': student_name,
                'average_grade': float(average_grade),
                'grades': grades,
                'activities': activities if activities else []
            })
            
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': results
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error getting top 3 students: {error}')
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500
        
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/top_by_district/', methods=['GET'])
@token_required
def top_by_district():
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'This endpoint is only available for staff members',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Query para obter o melhor aluno por distrito
        # Usando uma única query SQL com window functions
        cur.execute('''
            WITH student_averages AS (
                -- Calcular média de notas por aluno
                SELECT 
                    s.person_person_id as student_id,
                    p.address as district,
                    AVG(r.score) as average_grade,
                    -- Rank dentro do distrito
                    RANK() OVER (PARTITION BY p.address ORDER BY AVG(r.score) DESC) as district_rank
                FROM student s
                JOIN person p ON s.person_person_id = p.person_id
                JOIN result r ON s.person_person_id = r.student_person_person_id
                GROUP BY s.person_person_id, p.address
            )
            -- Selecionar apenas os melhores de cada distrito
            SELECT 
                student_id,
                district,
                ROUND(average_grade::numeric, 2) as average_grade
            FROM student_averages
            WHERE district_rank = 1
            ORDER BY average_grade DESC;
        ''')
        
        results = []
        for student_id, district, average_grade in cur.fetchall():
            results.append({
                'student_id': student_id,
                'district': district,
                'average_grade': float(average_grade)
            })
            
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': results
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error getting top students by district: {error}')
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500
        
    finally:
        if conn is not None:
            conn.close()


@app.route('/dbproj/report', methods=['GET'])
@token_required
def monthly_report():
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can access this information',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Query única para obter o relatório mensal dos últimos 12 meses
        cur.execute('''
            WITH monthly_course_stats AS (
                SELECT 
                    TO_CHAR(ex.data, 'YYYY-MM') as month,
                    e.edition_id as course_edition_id,
                    c.course_name as course_edition_name,
                    COUNT(DISTINCT r.student_person_person_id) as evaluated,
                    COUNT(DISTINCT CASE WHEN r.score >= 9.5 THEN r.student_person_person_id END) as approved,
                    ROW_NUMBER() OVER (
                        PARTITION BY TO_CHAR(ex.data, 'YYYY-MM')
                        ORDER BY COUNT(DISTINCT CASE WHEN r.score >= 9.5 THEN r.student_person_person_id END) DESC
                    ) as rank
                FROM result r
                JOIN exam ex ON r.exam_exam_id = ex.exam_id
                JOIN edition e ON ex.exam_id = e.exam_exam_id
                JOIN course c ON e.course_course_id = c.course_id
                WHERE EXTRACT(YEAR FROM ex.data) = 
                    CASE 
                        WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 THEN EXTRACT(YEAR FROM CURRENT_DATE)
                        ELSE EXTRACT(YEAR FROM CURRENT_DATE) - 1
                    END
                GROUP BY month, e.edition_id, c.course_name
            )
            SELECT 
                month,
                course_edition_id,
                course_edition_name,
                approved,
                evaluated
            FROM monthly_course_stats
            WHERE rank = 1
            ORDER BY month DESC;
        ''')
        
        results = []
        for row in cur.fetchall():
            results.append({
                'month': row[0],
                'course_edition_id': row[1],
                'course_edition_name': row[2],
                'approved': row[3],
                'evaluated': row[4]
            })
            
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': results
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error generating monthly report: {error}')
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500
        
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/delete_details/<int:student_id>', methods=['DELETE'])
@token_required
def delete_student_details(student_id):
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff members can delete student data'
        }), 403
    
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se o estudante existe
        cur.execute('SELECT person_person_id FROM student WHERE person_person_id = %s', (student_id,))
        if cur.fetchone() is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student not found'
            }), 404
            
        # Deletar registros nas tabelas relacionadas ao estudante
        # Deletar referências nas tabelas relacionadas a student
        cur.execute('DELETE FROM exam_student WHERE student_person_person_id = %s', (student_id,))
        cur.execute('DELETE FROM student_course WHERE student_person_person_id = %s', (student_id,))
        cur.execute('DELETE FROM extraactivities_student WHERE student_person_person_id = %s', (student_id,))
        cur.execute('DELETE FROM attendance WHERE student_person_person_id = %s', (student_id,))
        cur.execute('DELETE FROM result WHERE student_person_person_id = %s', (student_id,))
        cur.execute('DELETE FROM major_info WHERE student_person_person_id = %s', (student_id,))
        cur.execute('DELETE FROM extraactivities_fees WHERE student_person_person_id = %s', (student_id,))
        # Deletar da tabela student
        cur.execute('DELETE FROM student WHERE person_person_id = %s', (student_id,))
        
        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success']
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error deleting student data: {error}')
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }), 500
        
    finally:
        if conn is not None:
            conn.close()

@app.route('/dbproj/student/financial-status/<int:student_id>', methods=['GET'])
@token_required
def student_financial_status(student_id):
    # Verificar se o usuário é staff ou o próprio estudante
    if flask.g.role != 'staff' and str(flask.g.person_id) != str(student_id):
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only staff or the student themselves can access this information',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Obter informações financeiras do estudante
        cur.execute('''
            WITH student_majors AS (
                SELECT 
                    s.person_person_id,
                    m.major_name,
                    mi.fees as tuition_fee,
                    fa.values_acumulate as paid_amount,
                    mi.status
                FROM student s
                JOIN major_info mi ON s.person_person_id = mi.student_person_person_id
                JOIN major m ON mi.major_major_id = m.major_id
                JOIN fees_account fa ON mi.fees_account_fees_account_id = fa.fees_account_id
                WHERE s.person_person_id = %s
            ),
            student_activities AS (
                SELECT 
                    s.person_person_id,
                    ea.name as activity_name,
                    ef.fees as activity_fee,
                    fa.values_acumulate as paid_amount,
                    ef.status
                FROM student s
                JOIN extraactivities_student eas ON s.person_person_id = eas.student_person_person_id
                JOIN extraactivities ea ON eas.extraactivities_activity_id = ea.activity_id
                LEFT JOIN extraactivities_fees ef ON s.person_person_id = ef.student_person_person_id
                    AND eas.extraactivities_activity_id = ef.extraactivities_activity_id
                LEFT JOIN fees_account fa ON ef.fees_account_fees_account_id = fa.fees_account_id
                WHERE s.person_person_id = %s
            )
            SELECT 
                COALESCE(
                json_agg(
                    json_build_object(
                            'major_name', sm.major_name,
                            'tuition_fee', sm.tuition_fee,
                            'paid_amount', COALESCE(sm.paid_amount, 0),
                            'pending_amount', sm.tuition_fee - COALESCE(sm.paid_amount, 0),
                            'status', sm.status
                        )
                    ) FILTER (WHERE sm.major_name IS NOT NULL),
                    '[]'
                ) as majors,
                COALESCE(
                json_agg(
                    json_build_object(
                            'activity_name', sa.activity_name,
                            'activity_fee', sa.activity_fee,
                            'paid_amount', COALESCE(sa.paid_amount, 0),
                            'pending_amount', sa.activity_fee - COALESCE(sa.paid_amount, 0),
                            'status', sa.status
                        )
                    ) FILTER (WHERE sa.activity_name IS NOT NULL),
                    '[]'
                ) as activities
            FROM student_majors sm
            FULL OUTER JOIN student_activities sa ON sm.person_person_id = sa.person_person_id;
        ''', (student_id, student_id))
        
        result = cur.fetchone()
        
        if result is None or (result[0] is None and result[1] is None):
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student not found or not enrolled in any major/activity',
                'results': None
            }), 404
            
        majors_data, activities_data = result
        
        # Processar informações dos majors
        majors = []
        total_majors_fees = 0
        total_majors_paid = 0
        
        if majors_data:
            for major in majors_data:
                tuition_fee = float(major['tuition_fee']) if major['tuition_fee'] else 0
                paid_amount = float(major['paid_amount']) if major['paid_amount'] else 0
                pending_amount = float(major['pending_amount']) if major['pending_amount'] else 0
                
                majors.append({
                    'name': major['major_name'],
                    'tuition_fee': tuition_fee,
                    'paid_amount': paid_amount,
                    'pending_amount': pending_amount,
                    'status': major['status']
                })
                
                total_majors_fees += tuition_fee
                total_majors_paid += paid_amount
        
        # Processar atividades extracurriculares
        activities = []
        total_activities_fees = 0
        total_activities_paid = 0
        
        if activities_data:
            for activity in activities_data:
                if activity['activity_name'] is not None:
                    activity_fee = float(activity['activity_fee']) if activity['activity_fee'] else 0
                    paid_amount = float(activity['paid_amount']) if activity['paid_amount'] else 0
                    pending_amount = float(activity['pending_amount']) if activity['pending_amount'] else 0
                    
                    activities.append({
                        'name': activity['activity_name'],
                        'activity_fee': activity_fee,
                        'paid_amount': paid_amount,
                        'pending_amount': pending_amount,
                        'status': activity['status']
                    })
                    
                    total_activities_fees += activity_fee
                    total_activities_paid += paid_amount
        
        # Calcular totais gerais
        total_fees = total_majors_fees + total_activities_fees
        total_paid = total_majors_paid + total_activities_paid
        total_pending = total_fees - total_paid
        
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'majors': majors,
                'majors_summary': {
                    'total_fees': total_majors_fees,
                    'total_paid': total_majors_paid,
                    'total_pending': total_majors_fees - total_majors_paid
                },
                'activities': activities,
                'activities_summary': {
                    'total_fees': total_activities_fees,
                    'total_paid': total_activities_paid,
                    'total_pending': total_activities_fees - total_activities_paid
                },
                'overall_summary': {
                    'total_fees': total_fees,
                    'total_paid': total_paid,
                    'total_pending': total_pending
                }
            }
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error getting student financial status: {error}')
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
