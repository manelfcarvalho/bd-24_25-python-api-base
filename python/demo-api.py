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
                # Adicionar campos obrigatórios para student se não fornecidos
                enrolment_date = payload.get('enrolment_date', datetime.date.today())
                mean = payload.get('mean', 0.0)
                
                # Inserir na tabela student
                cur.execute('''
                    INSERT INTO student (person_person_id, enrolment_date, mean)
                    VALUES (%s, %s, %s)
                ''', (person_id, enrolment_date, mean))
                
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
            else:
                # Role inválida
                conn.rollback()
                response = {
                    'status': StatusCodes['api_error'],
                    'errors': f'Invalid role: {role}. Must be one of: student, instructor, staff'
                }
                return flask.jsonify(response), 400

        conn.commit()
        response = {
            'status': StatusCodes['success'],
            'results': {
                'person_id': person_id,
                'role': role,
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
