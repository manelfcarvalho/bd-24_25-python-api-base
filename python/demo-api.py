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
        # Primeiro inserir na tabela person
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
        
        # Verificar se foi especificada uma role
        role = payload.get('role')
        
        if role:
            if role == 'student':
                # Verificar se já existe um major especificado
                major_id = payload.get('major_id')
                
                # Adicionar campos obrigatórios para student se não fornecidos
                enrolment_date = payload.get('enrolment_date', datetime.date.today())
                mean = payload.get('mean', 0.0)
                
                # Inserir na tabela student
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
                
            elif role in ['instructor', 'staff']:
                # Adicionar campos obrigatórios para worker se não fornecidos
                salary = payload.get('salary', 0.0)
                started_working = payload.get('started_working', datetime.date.today())
                
                # Inserir na tabela worker
                cur.execute('''
                    INSERT INTO worker (person_person_id, salary, started_working)
                    VALUES (%s, %s, %s)
                ''', (person_id, salary, started_working))
                
                if role == 'instructor':
                    # Campos obrigatórios para instructor
                    major = payload.get('major', 'General')
                    # Verificar se temos department_id
                    if 'department_id' not in payload:
                        # Se não tiver, pegar o primeiro departamento disponível
                        cur.execute('SELECT department_id FROM department LIMIT 1')
                        dept_result = cur.fetchone()
                        if dept_result:
                            department_id = dept_result[0]
                        else:
                            # Criar um departamento padrão se não existir nenhum
                            cur.execute('''
                                INSERT INTO department (name)
                                VALUES ('Default Department')
                                RETURNING department_id
                            ''')
                            department_id = cur.fetchone()[0]
                    else:
                        department_id = payload['department_id']
                    
                    # Inserir na tabela instructor
                    cur.execute('''
                        INSERT INTO instructor (worker_person_person_id, major, department_department_id)
                        VALUES (%s, %s, %s)
                    ''', (person_id, major, department_id))
                    
                elif role == 'staff':
                    # Inserir na tabela staff
                    cur.execute('''
                        INSERT INTO staff (worker_person_person_id)
                        VALUES (%s)
                    ''', (person_id,))

        conn.commit()
        response = {
            'status': StatusCodes['success'],
            'results': {
                'person_id': person_id,
                'role': role
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
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Username, email, and password are required',
            'results': None
        })
    
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Inserir na tabela person primeiro
        cur.execute('''
            INSERT INTO person (name, email, password)
            VALUES (%s, %s, %s)
            RETURNING person_id
        ''', (username, email, password))
        
        person_id = cur.fetchone()[0]
        
        # Inserir na tabela student
        cur.execute('''
            INSERT INTO student (person_person_id, enrolment_date)
            VALUES (%s, CURRENT_DATE)
        ''', (person_id,))
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': person_id}
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
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    salary = data.get('salary', 0.0)

    if not username or not email or not password:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Username, email, and password are required',
            'results': None
        })
    
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Inserir na tabela person primeiro
        cur.execute('''
            INSERT INTO person (name, email, password)
            VALUES (%s, %s, %s)
            RETURNING person_id
        ''', (username, email, password))
        
        person_id = cur.fetchone()[0]
        
        # Inserir na tabela worker
        cur.execute('''
            INSERT INTO worker (person_person_id, salary, started_working)
            VALUES (%s, %s, CURRENT_DATE)
        ''', (person_id, salary))
        
        # Inserir na tabela staff
        cur.execute('''
            INSERT INTO staff (worker_person_person_id)
            VALUES (%s)
        ''', (person_id,))
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': person_id}
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
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    salary = data.get('salary', 0.0)
    major = data.get('major', 'General')
    department_id = data.get('department_id')

    if not username or not email or not password:
        return flask.jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Username, email, and password are required',
            'results': None
        })
    
    conn = db_connection()
    cur = conn.cursor()
    
    try:
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
        
        # Inserir na tabela person primeiro
        cur.execute('''
            INSERT INTO person (name, email, password)
            VALUES (%s, %s, %s)
            RETURNING person_id
        ''', (username, email, password))
        
        person_id = cur.fetchone()[0]
        
        # Inserir na tabela worker
        cur.execute('''
            INSERT INTO worker (person_person_id, salary, started_working)
            VALUES (%s, %s, CURRENT_DATE)
        ''', (person_id, salary))
        
        # Inserir na tabela instructor
        cur.execute('''
            INSERT INTO instructor (worker_person_person_id, major, department_department_id)
            VALUES (%s, %s, %s)
        ''', (person_id, major, department_id))
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': person_id}
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
    # Verificar se o usuário é estudante
    if flask.g.role != 'student':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only students can enroll in majors',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se o estudante já está matriculado em algum major
        cur.execute('''
            SELECT m.major_name 
            FROM major_info mi
            JOIN major m ON mi.major_major_id = m.major_id
            WHERE mi.student_person_person_id = %s AND mi.status = 'Active'
        ''', (flask.g.person_id,))
        
        existing_major = cur.fetchone()
        if existing_major:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': f'Student is already enrolled in major: {existing_major[0]}. Must unenroll first.',
                'results': None
            }), 400

        # Verificar se o major existe
        cur.execute('SELECT major_name FROM major WHERE major_id = %s', (major_id,))
        major = cur.fetchone()
        if not major:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Major not found',
                'results': None
            }), 404

        # Criar nova conta de taxas
        cur.execute('INSERT INTO fees_account (values_acumulate) VALUES (0) RETURNING fees_account_id')
        fees_account_id = cur.fetchone()[0]

        # Matricular o estudante no novo major
        cur.execute('''
            INSERT INTO major_info (student_person_person_id, major_major_id, fees, status, fees_account_fees_account_id)
            VALUES (%s, %s, %s, 'Active', %s)
        ''', (flask.g.person_id, major_id, 5000.00, fees_account_id))

        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': f'Successfully enrolled in major: {major[0]}'
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
    # Verificar se o usuário é estudante
    if flask.g.role != 'student':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'Only students can unenroll from majors',
            'results': None
        }), 403

    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar se o estudante está matriculado em algum major
        cur.execute('''
            SELECT m.major_name, mi.major_major_id
            FROM major_info mi
            JOIN major m ON mi.major_major_id = m.major_id
            WHERE mi.student_person_person_id = %s AND mi.status = 'Active'
        ''', (flask.g.person_id,))
        
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
            WHERE student_person_person_id = %s AND major_major_id = %s
        ''', (flask.g.person_id, current_major[1]))

        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': f'Successfully unenrolled from major: {current_major[0]}'
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

@app.route('/dbproj/student_details/<int:student_id>', methods=['GET'])
@token_required
def student_details(student_id):
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
        # Buscar informações do estudante e seu major atual
        cur.execute('''
            WITH student_info AS (
                SELECT 
                    p.name as student_name,
                    p.email,
                    p.address,
                    s.enrolment_date,
                    s.mean as overall_mean
                FROM student s
                JOIN person p ON s.person_person_id = p.person_id
                WHERE s.person_person_id = %s
            ),
            current_major AS (
                SELECT 
                    m.major_name,
                    m.major_id,
                    mi.fees,
                    mi.status
                FROM major_info mi
                JOIN major m ON mi.major_major_id = m.major_id
                WHERE mi.student_person_person_id = %s AND mi.status = 'Active'
            ),
            course_results AS (
                SELECT 
                    e.edition_id,
                    c.name as course_name,
                    e.year,
                    r.grade
                FROM result r
                JOIN edition e ON r.edition_edition_id = e.edition_id
                JOIN course c ON e.course_course_id = c.course_id
                WHERE r.student_person_person_id = %s
                ORDER BY e.year DESC, e.edition_id DESC
            )
            SELECT 
                si.*,
                cm.*,
                json_agg(
                    json_build_object(
                        'course_edition_id', cr.edition_id,
                        'course_name', cr.course_name,
                        'year', cr.year,
                        'grade', cr.grade
                    )
                ) as course_results
            FROM student_info si
            LEFT JOIN current_major cm ON true
            LEFT JOIN course_results cr ON true
            GROUP BY 
                si.student_name, si.email, si.address, si.enrolment_date, si.overall_mean,
                cm.major_name, cm.major_id, cm.fees, cm.status
        ''', (student_id, student_id, student_id))
        
        result = cur.fetchone()
        if not result:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student not found',
                'results': None
            }), 404
            
        # Processar os resultados
        student_name, email, address, enrolment_date, overall_mean, major_name, major_id, fees, major_status, course_results = result
        
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'student_info': {
                    'name': student_name,
                    'email': email,
                    'address': address,
                    'enrolment_date': enrolment_date.strftime('%Y-%m-%d') if enrolment_date else None,
                    'overall_mean': float(overall_mean) if overall_mean is not None else None
                },
                'current_major': {
                    'name': major_name,
                    'major_id': major_id,
                    'fees': float(fees) if fees is not None else None,
                    'status': major_status
                } if major_name else None,
                'course_results': course_results if course_results and course_results[0] is not None else []
            }
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
        # Query única para obter todos os detalhes necessários
        cur.execute('''
            WITH enrolled_counts AS (
                SELECT 
                    e.edition_id,
                    COUNT(DISTINCT sc.student_person_person_id) as enrolled_count,
                    COUNT(DISTINCT CASE WHEN r.grade >= 10 THEN r.student_person_person_id END) as approved_count
                FROM edition e
                LEFT JOIN student_course sc ON e.edition_id = sc.edition_edition_id
                LEFT JOIN result r ON e.edition_id = r.edition_edition_id
                GROUP BY e.edition_id
            ),
            edition_instructors AS (
                SELECT 
                    e.edition_id,
                    ARRAY_AGG(DISTINCT i.worker_person_person_id) as instructor_ids
                FROM edition e
                LEFT JOIN instructor i ON e.coordinator_instructor_worker_person_person_id = i.worker_person_person_id
                GROUP BY e.edition_id
            )
            SELECT 
                c.course_id,
                c.name as course_name,
                e.edition_id,
                e.year,
                e.capacity,
                ec.enrolled_count,
                ec.approved_count,
                e.coordinator_instructor_worker_person_person_id,
                ei.instructor_ids
            FROM course c
            JOIN edition e ON c.course_id = e.course_course_id
            JOIN enrolled_counts ec ON e.edition_id = ec.edition_id
            JOIN edition_instructors ei ON e.edition_id = ei.edition_id
            WHERE c.degree_degree_id = %s
            ORDER BY e.year DESC, c.name
        ''', (degree_id,))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'course_id': row[0],
                'course_name': row[1],
                'course_edition_id': row[2],
                'course_edition_year': row[3],
                'capacity': row[4],
                'enrolled_count': row[5],
                'approved_count': row[6],
                'coordinator_id': row[7],
                'instructors': row[8] if row[8] is not None else []
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
        # Query única para obter top 3 estudantes
        cur.execute('''
            WITH student_grades AS (
                SELECT 
                    s.person_person_id,
                    p.name as student_name,
                    AVG(r.grade) as average_grade,
                    ARRAY_AGG(DISTINCT ea.activity_id) as activities,
                    ROW_NUMBER() OVER (ORDER BY AVG(r.grade) DESC) as rank
                FROM student s
                JOIN person p ON s.person_person_id = p.person_id
                LEFT JOIN result r ON s.person_person_id = r.student_person_person_id
                LEFT JOIN extraactivities_student eas ON s.person_person_id = eas.student_person_person_id
                LEFT JOIN extraactivities ea ON eas.extraactivities_activity_id = ea.activity_id
                WHERE EXTRACT(YEAR FROM r.date) = EXTRACT(YEAR FROM CURRENT_DATE)
                GROUP BY s.person_person_id, p.name
            )
            SELECT 
                sg.student_name,
                sg.average_grade,
                sg.activities,
                e.edition_id,
                c.name as course_name,
                r.grade,
                r.date
            FROM student_grades sg
            JOIN result r ON sg.person_person_id = r.student_person_person_id
            JOIN edition e ON r.edition_edition_id = e.edition_id
            JOIN course c ON e.course_course_id = c.course_id
            WHERE sg.rank <= 3
            ORDER BY sg.average_grade DESC, r.date DESC
        ''')
        
        current_student = None
        results = []
        student_data = {}
        
        for row in cur.fetchall():
            student_name = row[0]
            
            if student_name != current_student:
                if current_student is not None:
                    results.append(student_data)
                current_student = student_name
                student_data = {
                    'student_name': student_name,
                    'average_grade': float(row[1]),
                    'grades': [],
                    'activities': row[2] if row[2] is not None else []
                }
            
            student_data['grades'].append({
                'course_edition_id': row[3],
                'course_edition_name': row[4],
                'grade': float(row[5]) if row[5] is not None else None,
                'date': row[6].strftime('%Y-%m-%d') if row[6] is not None else None
            })
        
        if current_student is not None:
            results.append(student_data)
            
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
        # Query única para obter relatório mensal dos últimos 12 meses
        cur.execute('''
            WITH monthly_stats AS (
                SELECT 
                    TO_CHAR(r.date, 'YYYY-MM') as month,
                    e.edition_id,
                    c.name as course_name,
                    COUNT(DISTINCT r.student_person_person_id) as evaluated,
                    COUNT(DISTINCT CASE WHEN r.grade >= 10 THEN r.student_person_person_id END) as approved,
                    ROW_NUMBER() OVER (PARTITION BY TO_CHAR(r.date, 'YYYY-MM') 
                                     ORDER BY COUNT(DISTINCT CASE WHEN r.grade >= 10 
                                                                 THEN r.student_person_person_id END) DESC) as rank
                FROM result r
                JOIN edition e ON r.edition_edition_id = e.edition_id
                JOIN course c ON e.course_course_id = c.course_id
                WHERE r.date >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY month, e.edition_id, c.name
            )
            SELECT 
                month,
                edition_id,
                course_name,
                approved,
                evaluated
            FROM monthly_stats
            WHERE rank = 1
            ORDER BY month DESC
        ''')
        
        results = []
        for month, edition_id, course_name, approved, evaluated in cur.fetchall():
            results.append({
                'month': month,
                'course_edition_id': edition_id,
                'course_edition_name': course_name,
                'approved': approved,
                'evaluated': evaluated
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

@app.route('/dbproj/delete_person/<int:person_id>', methods=['DELETE'])
@token_required
def delete_person(person_id):
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
            }), 404
            
        # Verificar qual é o tipo de usuário (student, instructor, staff)
        role = None
        
        # Verificar se é student
        cur.execute('SELECT person_person_id FROM student WHERE person_person_id = %s', (person_id,))
        is_student = cur.fetchone() is not None
        if is_student:
            role = 'student'
            
        # Verificar se é instructor
        cur.execute('SELECT worker_person_person_id FROM instructor WHERE worker_person_person_id = %s', (person_id,))
        is_instructor = cur.fetchone() is not None
        if is_instructor:
            role = 'instructor'
            
        # Verificar se é staff
        cur.execute('SELECT worker_person_person_id FROM staff WHERE worker_person_person_id = %s', (person_id,))
        is_staff = cur.fetchone() is not None
        if is_staff:
            role = 'staff'
            
        # Deletar registros nas tabelas relacionadas
        if role == 'student':
            # Deletar referências nas tabelas relacionadas a student
            cur.execute('DELETE FROM exam_student WHERE student_person_person_id = %s', (person_id,))
            cur.execute('DELETE FROM student_course WHERE student_person_person_id = %s', (person_id,))
            cur.execute('DELETE FROM extraactivities_student WHERE student_person_person_id = %s', (person_id,))
            cur.execute('DELETE FROM attendance WHERE student_person_person_id = %s', (person_id,))
            cur.execute('DELETE FROM result WHERE student_person_person_id = %s', (person_id,))
            cur.execute('DELETE FROM major_info WHERE student_person_person_id = %s', (person_id,))
            cur.execute('DELETE FROM extraactivities_fees WHERE student_person_person_id = %s', (person_id,))
            # Deletar da tabela student
            cur.execute('DELETE FROM student WHERE person_person_id = %s', (person_id,))
            
        elif role == 'instructor':
            # Verificar se é coordinator e deletar referências
            cur.execute('SELECT instructor_worker_person_person_id FROM coordinator WHERE instructor_worker_person_person_id = %s', (person_id,))
            is_coordinator = cur.fetchone() is not None
            if is_coordinator:
                # Atualizar edições que usam este coordinator (definindo NULL ou outro coordinator)
                cur.execute('''
                    UPDATE edition 
                    SET coordinator_instructor_worker_person_person_id = NULL
                    WHERE coordinator_instructor_worker_person_person_id = %s
                ''', (person_id,))
                # Deletar da tabela coordinator
                cur.execute('DELETE FROM coordinator WHERE instructor_worker_person_person_id = %s', (person_id,))
                
            # Verificar se é assistant e deletar referências
            cur.execute('SELECT instructor_worker_person_person_id FROM assistant WHERE instructor_worker_person_person_id = %s', (person_id,))
            is_assistant = cur.fetchone() is not None
            if is_assistant:
                # Deletar referências da tabela assistant_class
                cur.execute('DELETE FROM assistant_class WHERE assistant_instructor_worker_person_person_id = %s', (person_id,))
                # Deletar da tabela assistant
                cur.execute('DELETE FROM assistant WHERE instructor_worker_person_person_id = %s', (person_id,))
                
            # Deletar da tabela instructor
            cur.execute('DELETE FROM instructor WHERE worker_person_person_id = %s', (person_id,))
            # Deletar da tabela worker
            cur.execute('DELETE FROM worker WHERE person_person_id = %s', (person_id,))
            
        elif role == 'staff':
            # Deletar da tabela staff
            cur.execute('DELETE FROM staff WHERE worker_person_person_id = %s', (person_id,))
            # Deletar da tabela worker
            cur.execute('DELETE FROM worker WHERE person_person_id = %s', (person_id,))
        
        # Finalmente, deletar da tabela person
        cur.execute('DELETE FROM person WHERE person_id = %s', (person_id,))
        
        conn.commit()
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': f'Person with ID {person_id} successfully deleted'
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error deleting person: {error}')
        conn.rollback()
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
        }), 500
        
    finally:
        if conn is not None:
            conn.close()


@app.route('/dbproj/student-portal', methods=['GET'])
@token_required
def student_portal():
    # Verificar se o usuário autenticado é um estudante
    if flask.g.role != 'student':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'This endpoint is only available for students',
            'results': None
        }), 403
    
    # Aqui o usuário é estudante, podemos continuar
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        person_id = flask.g.person_id
        
        # Obter informações dos cursos em que o estudante está matriculado
        cur.execute('''
            SELECT c.course_id, c.course_name
            FROM course c
            JOIN student_course sc ON c.course_id = sc.course_course_id
            WHERE sc.student_person_person_id = %s
        ''', (person_id,))
        
        courses = []
        for course_id, course_name in cur.fetchall():
            courses.append({
                'course_id': course_id,
                'course_name': course_name
            })
        
        # Obter atividades extracurriculares do estudante
        cur.execute('''
            SELECT e.activity_id, e.name, e.description
            FROM extraactivities e
            JOIN extraactivities_student es ON e.activity_id = es.extraactivities_activity_id
            WHERE es.student_person_person_id = %s
        ''', (person_id,))
        
        activities = []
        for activity_id, name, description in cur.fetchall():
            activities.append({
                'activity_id': activity_id,
                'name': name,
                'description': description
            })
        
        # Retornar informações do portal do estudante
        return flask.jsonify({
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'welcome_message': f'Bem-vindo ao Portal do Estudante, {flask.g.name}!',
                'enrolled_courses': courses,
                'extracurricular_activities': activities,
                'portal_features': [
                    'Consultar notas',
                    'Ver horário de aulas',
                    'Gerenciar inscrições',
                    'Acessar material de estudo',
                    'Contactar professores'
                ]
            }
        })
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error in student portal: {error}')
        return flask.jsonify({
            'status': StatusCodes['internal_error'],
            'errors': str(error),
            'results': None
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
        # Obter informações de todos os majors e seus custos
        cur.execute('''
            WITH major_costs AS (
                SELECT 
                    m.student_person_person_id,
                    m.major_name,
                    m.tuition_fee,
                    m.enrollment_date,
                    COALESCE(SUM(mp.amount), 0) as total_paid,
                    ROW_NUMBER() OVER (PARTITION BY m.student_person_person_id ORDER BY m.enrollment_date DESC) as major_order
                FROM major_info m
                LEFT JOIN major_payments mp ON m.student_person_person_id = mp.student_person_person_id 
                    AND m.major_name = mp.major_name
                WHERE m.student_person_person_id = %s
                GROUP BY m.student_person_person_id, m.major_name, m.tuition_fee, m.enrollment_date
            ),
            extra_activities_costs AS (
                SELECT 
                    ea.student_person_person_id,
                    e.name as activity_name,
                    e.fee as activity_fee,
                    COALESCE(SUM(ef.amount_paid), 0) as total_paid
                FROM extraactivities_student ea
                JOIN extraactivities e ON ea.extraactivities_activity_id = e.activity_id
                LEFT JOIN extraactivities_fees ef ON ea.student_person_person_id = ef.student_person_person_id 
                    AND ea.extraactivities_activity_id = ef.extraactivities_activity_id
                WHERE ea.student_person_person_id = %s
                GROUP BY ea.student_person_person_id, e.name, e.fee
            )
            SELECT 
                json_agg(
                    json_build_object(
                        'major_name', mc.major_name,
                        'tuition_fee', mc.tuition_fee,
                        'total_paid', mc.total_paid,
                        'enrollment_date', mc.enrollment_date
                    )
                ) as majors,
                json_agg(
                    json_build_object(
                        'activity_name', eac.activity_name,
                        'activity_fee', eac.activity_fee,
                        'total_paid', eac.total_paid
                    )
                ) as extra_activities
            FROM major_costs mc
            LEFT JOIN extra_activities_costs eac ON mc.student_person_person_id = eac.student_person_person_id
            GROUP BY mc.student_person_person_id
        ''', (student_id, student_id))
        
        result = cur.fetchone()
        
        if result is None or result[0] is None:
            return flask.jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Student not found or not enrolled in any major',
                'results': None
            }), 404
            
        majors_data, extra_activities = result
        
        # Processar informações dos majors
        majors = []
        total_majors_fees = 0
        total_majors_paid = 0
        
        for major in majors_data:
            tuition_fee = float(major['tuition_fee']) if major['tuition_fee'] else 0
            total_paid = float(major['total_paid']) if major['total_paid'] else 0
            pending = tuition_fee - total_paid
            
            majors.append({
                'name': major['major_name'],
                'enrollment_date': major['enrollment_date'].strftime('%Y-%m-%d') if major['enrollment_date'] else None,
                'tuition_fee': tuition_fee,
                'paid': total_paid,
                'pending': pending
            })
            
            total_majors_fees += tuition_fee
            total_majors_paid += total_paid
        
        # Processar atividades extracurriculares
        activities = []
        total_activities_fees = 0
        total_activities_paid = 0
        
        if extra_activities and extra_activities[0] is not None:
            for activity in extra_activities:
                if activity['activity_name'] is not None:  # Verificar se a atividade é válida
                    activity_fee = float(activity['activity_fee']) if activity['activity_fee'] else 0
                    total_paid = float(activity['total_paid']) if activity['total_paid'] else 0
                    pending = activity_fee - total_paid
                    
                    activities.append({
                        'name': activity['activity_name'],
                        'total_fee': activity_fee,
                        'paid': total_paid,
                        'pending': pending
                    })
                    
                    total_activities_fees += activity_fee
                    total_activities_paid += total_paid
        
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
                'extra_activities': activities,
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
                    AVG(r.grade) as average_grade,
                    -- Rank dentro do distrito
                    RANK() OVER (PARTITION BY p.address ORDER BY AVG(r.grade) DESC) as district_rank
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

@app.route('/dbproj/delete_details/{student_id}', methods=['DELETE'])
@token_required
def delete_student_details(student_id):
    # Verificar se o usuário é staff
    if flask.g.role != 'staff':
        return flask.jsonify({
            'status': StatusCodes['unauthorized'],
            'errors': 'This endpoint is only available for staff members',
            'results': None
        }), 403
        
    return delete_person(student_id)  # Reutilizar a função existente

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
