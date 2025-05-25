CREATE TABLE person (
	person_id BIGSERIAL,
	name	 TEXT NOT NULL,
	age	 INTEGER NOT NULL,
	gender	 CHAR(255) NOT NULL,
	nif	 BIGINT NOT NULL,
	email	 TEXT,
	address	 TEXT NOT NULL,
	phone	 INTEGER NOT NULL,
	password	 VARCHAR(512) NOT NULL,
	PRIMARY KEY(person_id)
);

CREATE TABLE student (
	enrolment_date	 DATE NOT NULL,
	mean		 FLOAT(8) NOT NULL,
	person_person_id BIGINT,
	PRIMARY KEY(person_person_id)
);

CREATE TABLE worker (
	salary		 FLOAT(8) NOT NULL,
	started_working	 DATE NOT NULL,
	person_person_id BIGINT,
	PRIMARY KEY(person_person_id)
);

CREATE TABLE instructor (
	major			 TEXT NOT NULL,
	department_department_id BIGINT NOT NULL,
	worker_person_person_id	 BIGINT,
	PRIMARY KEY(worker_person_person_id)
);

CREATE TABLE staff (
	worker_person_person_id BIGINT,
	PRIMARY KEY(worker_person_person_id)
);

CREATE TABLE course (
	course_id	 BIGSERIAL,
	course_name	 TEXT NOT NULL,
	course_course_id BIGINT NOT NULL,
	PRIMARY KEY(course_id)
);

CREATE TABLE class (
	class_id	 SERIAL,
	type	 VARCHAR(2) NOT NULL,
	class_name TEXT NOT NULL,
	PRIMARY KEY(class_id)
);

CREATE TABLE classroom (
	classroom_id SERIAL,
	capacity	 BIGINT NOT NULL,
	location	 TEXT NOT NULL,
	PRIMARY KEY(classroom_id)
);

CREATE TABLE extraactivities (
	activity_id BIGSERIAL,
	name	 TEXT NOT NULL,
	description TEXT,
	PRIMARY KEY(activity_id)
);

CREATE TABLE exam (
	exam_id BIGSERIAL,
	data	 TIMESTAMP NOT NULL,
	type	 TEXT NOT NULL,
	PRIMARY KEY(exam_id)
);

CREATE TABLE result (
	result_id		 BIGSERIAL,
	score			 FLOAT(8) NOT NULL,
	exam_exam_id		 BIGINT,
	student_person_person_id BIGINT,
	PRIMARY KEY(result_id,exam_exam_id,student_person_person_id)
);

CREATE TABLE attendance (
	attendance_id		 BIGSERIAL,
	present			 BOOL NOT NULL,
	class_class_id		 INTEGER,
	student_person_person_id BIGINT,
	PRIMARY KEY(attendance_id,class_class_id,student_person_person_id)
);

CREATE TABLE department (
	department_id BIGSERIAL,
	name		 VARCHAR(512) NOT NULL,
	PRIMARY KEY(department_id)
);

CREATE TABLE period (
	period_id	 BIGSERIAL,
	start_time TIMESTAMP NOT NULL,
	end_time	 TIMESTAMP NOT NULL,
	PRIMARY KEY(period_id)
);

CREATE TABLE edition (
	edition_id					 SERIAL,
	capacity					 INTEGER NOT NULL,
	class_class_id				 INTEGER NOT NULL,
	exam_exam_id					 BIGINT NOT NULL,
	coordinator_instructor_worker_person_person_id BIGINT NOT NULL,
	course_course_id				 BIGINT NOT NULL,
	PRIMARY KEY(edition_id)
);

CREATE TABLE major (
	major_id	 BIGSERIAL,
	major_name	 TEXT NOT NULL,
	course_course_id BIGINT NOT NULL,
	PRIMARY KEY(major_id)
);

CREATE TABLE coordinator (
	instructor_worker_person_person_id BIGINT,
	PRIMARY KEY(instructor_worker_person_person_id)
);

CREATE TABLE assistant (
	instructor_worker_person_person_id BIGINT,
	PRIMARY KEY(instructor_worker_person_person_id)
);

CREATE TABLE payment (
	payment_id			 BIGSERIAL,
	paid_amount			 BIGINT,
	fees_account_fees_account_id BIGINT NOT NULL,
	PRIMARY KEY(payment_id)
);

CREATE TABLE fees_account (
	fees_account_id	 BIGSERIAL,
	values_acumulate FLOAT(8) NOT NULL,
	PRIMARY KEY(fees_account_id)
);

CREATE TABLE extraactivities_fees (
	fees			 FLOAT(8) NOT NULL,
	status			 VARCHAR(512),
	extraactivities_activity_id	 BIGINT NOT NULL,
	student_person_person_id	 BIGINT,
	fees_account_fees_account_id BIGINT NOT NULL,
	PRIMARY KEY(student_person_person_id)
);

CREATE TABLE major_info (
	fees			 FLOAT(8) NOT NULL,
	status			 VARCHAR(512),
	major_major_id		 BIGINT NOT NULL,
	student_person_person_id	 BIGINT,
	fees_account_fees_account_id BIGINT NOT NULL,
	PRIMARY KEY(student_person_person_id)
);

CREATE TABLE assistant_class (
	assistant_instructor_worker_person_person_id BIGINT,
	class_class_id				 INTEGER,
	PRIMARY KEY(assistant_instructor_worker_person_person_id,class_class_id)
);

CREATE TABLE student_course (
	student_person_person_id BIGINT,
	course_course_id	 BIGINT,
	PRIMARY KEY(student_person_person_id,course_course_id)
);

CREATE TABLE exam_student (
	exam_exam_id		 BIGINT,
	student_person_person_id BIGINT,
	PRIMARY KEY(exam_exam_id,student_person_person_id)
);

CREATE TABLE extraactivities_student (
	extraactivities_activity_id BIGINT,
	student_person_person_id	 BIGINT,
	PRIMARY KEY(extraactivities_activity_id,student_person_person_id)
);

CREATE TABLE class_period (
	class_class_id	 INTEGER,
	period_period_id BIGINT,
	PRIMARY KEY(class_class_id,period_period_id)
);

CREATE TABLE class_department (
	class_class_id		 INTEGER,
	department_department_id BIGINT,
	PRIMARY KEY(class_class_id,department_department_id)
);

CREATE TABLE class_classroom (
	class_class_id	 INTEGER,
	classroom_classroom_id INTEGER,
	PRIMARY KEY(class_class_id,classroom_classroom_id)
);

ALTER TABLE person ADD UNIQUE (nif, email);
ALTER TABLE person ADD CONSTRAINT constraint_0 CHECK (person_id > 0 AND age >= 0 );
ALTER TABLE student ADD CONSTRAINT student_fk1 FOREIGN KEY (person_person_id) REFERENCES person(person_id);
ALTER TABLE student ADD CONSTRAINT constraint_0 CHECK (mean >= 0);
ALTER TABLE worker ADD CONSTRAINT worker_fk1 FOREIGN KEY (person_person_id) REFERENCES person(person_id);
ALTER TABLE worker ADD CONSTRAINT constraint_0 CHECK (salary >= 0 );
ALTER TABLE instructor ADD CONSTRAINT instructor_fk1 FOREIGN KEY (department_department_id) REFERENCES department(department_id);
ALTER TABLE instructor ADD CONSTRAINT instructor_fk2 FOREIGN KEY (worker_person_person_id) REFERENCES worker(person_person_id);
ALTER TABLE staff ADD CONSTRAINT staff_fk1 FOREIGN KEY (worker_person_person_id) REFERENCES worker(person_person_id);
ALTER TABLE course ADD CONSTRAINT course_fk1 FOREIGN KEY (course_course_id) REFERENCES course(course_id);
ALTER TABLE class ADD CONSTRAINT constraint_0 CHECK (class_id > 0 );
ALTER TABLE classroom ADD CONSTRAINT constraint_0 CHECK (classroom_id > 0 and capacity >= 0 );
ALTER TABLE exam ADD CONSTRAINT constraint_0 CHECK (exam_id > 0 );
ALTER TABLE result ADD CONSTRAINT result_fk1 FOREIGN KEY (exam_exam_id) REFERENCES exam(exam_id);
ALTER TABLE result ADD CONSTRAINT result_fk2 FOREIGN KEY (student_person_person_id) REFERENCES student(person_person_id);
ALTER TABLE result ADD CONSTRAINT constraint_0 CHECK (result_id > 0 and score >= 0 and score <= 20);
ALTER TABLE attendance ADD CONSTRAINT attendance_fk1 FOREIGN KEY (class_class_id) REFERENCES class(class_id);
ALTER TABLE attendance ADD CONSTRAINT attendance_fk2 FOREIGN KEY (student_person_person_id) REFERENCES student(person_person_id);
ALTER TABLE attendance ADD CONSTRAINT constraint_0 CHECK (attendance_id > 0 );
ALTER TABLE department ADD CONSTRAINT constraint_0 CHECK (department_id > 0 );
ALTER TABLE period ADD CONSTRAINT constraint_0 CHECK (period_id > 0 );
ALTER TABLE edition ADD CONSTRAINT edition_fk1 FOREIGN KEY (class_class_id) REFERENCES class(class_id);
ALTER TABLE edition ADD CONSTRAINT edition_fk2 FOREIGN KEY (exam_exam_id) REFERENCES exam(exam_id);
ALTER TABLE edition ADD CONSTRAINT edition_fk3 FOREIGN KEY (coordinator_instructor_worker_person_person_id) REFERENCES coordinator(instructor_worker_person_person_id);
ALTER TABLE edition ADD CONSTRAINT edition_fk4 FOREIGN KEY (course_course_id) REFERENCES course(course_id);
ALTER TABLE edition ADD CONSTRAINT constraint_0 CHECK (edition_id > 0 AND capacity >= 0 );
ALTER TABLE major ADD CONSTRAINT major_fk1 FOREIGN KEY (course_course_id) REFERENCES course(course_id);
ALTER TABLE coordinator ADD CONSTRAINT coordinator_fk1 FOREIGN KEY (instructor_worker_person_person_id) REFERENCES instructor(worker_person_person_id);
ALTER TABLE assistant ADD CONSTRAINT assistant_fk1 FOREIGN KEY (instructor_worker_person_person_id) REFERENCES instructor(worker_person_person_id);
ALTER TABLE payment ADD CONSTRAINT payment_fk1 FOREIGN KEY (fees_account_fees_account_id) REFERENCES fees_account(fees_account_id);
ALTER TABLE extraactivities_fees ADD UNIQUE (status, extraactivities_activity_id);
ALTER TABLE extraactivities_fees ADD CONSTRAINT extraactivities_fees_fk1 FOREIGN KEY (extraactivities_activity_id) REFERENCES extraactivities(activity_id);
ALTER TABLE extraactivities_fees ADD CONSTRAINT extraactivities_fees_fk2 FOREIGN KEY (student_person_person_id) REFERENCES student(person_person_id);
ALTER TABLE extraactivities_fees ADD CONSTRAINT extraactivities_fees_fk3 FOREIGN KEY (fees_account_fees_account_id) REFERENCES fees_account(fees_account_id);
ALTER TABLE extraactivities_fees ADD CONSTRAINT constraint_0 CHECK (fees >= 0);
ALTER TABLE major_info ADD UNIQUE (major_major_id);
ALTER TABLE major_info ADD CONSTRAINT major_info_fk1 FOREIGN KEY (major_major_id) REFERENCES major(major_id);
ALTER TABLE major_info ADD CONSTRAINT major_info_fk2 FOREIGN KEY (student_person_person_id) REFERENCES student(person_person_id);
ALTER TABLE major_info ADD CONSTRAINT major_info_fk3 FOREIGN KEY (fees_account_fees_account_id) REFERENCES fees_account(fees_account_id);
ALTER TABLE major_info ADD CONSTRAINT constraint_0 CHECK (fees >= 0);
ALTER TABLE assistant_class ADD CONSTRAINT assistant_class_fk1 FOREIGN KEY (assistant_instructor_worker_person_person_id) REFERENCES assistant(instructor_worker_person_person_id);
ALTER TABLE assistant_class ADD CONSTRAINT assistant_class_fk2 FOREIGN KEY (class_class_id) REFERENCES class(class_id);
ALTER TABLE student_course ADD CONSTRAINT student_course_fk1 FOREIGN KEY (student_person_person_id) REFERENCES student(person_person_id);
ALTER TABLE student_course ADD CONSTRAINT student_course_fk2 FOREIGN KEY (course_course_id) REFERENCES course(course_id);
ALTER TABLE exam_student ADD CONSTRAINT exam_student_fk1 FOREIGN KEY (exam_exam_id) REFERENCES exam(exam_id);
ALTER TABLE exam_student ADD CONSTRAINT exam_student_fk2 FOREIGN KEY (student_person_person_id) REFERENCES student(person_person_id);
ALTER TABLE extraactivities_student ADD CONSTRAINT extraactivities_student_fk1 FOREIGN KEY (extraactivities_activity_id) REFERENCES extraactivities(activity_id);
ALTER TABLE extraactivities_student ADD CONSTRAINT extraactivities_student_fk2 FOREIGN KEY (student_person_person_id) REFERENCES student(person_person_id);
ALTER TABLE class_period ADD CONSTRAINT class_period_fk1 FOREIGN KEY (class_class_id) REFERENCES class(class_id);
ALTER TABLE class_period ADD CONSTRAINT class_period_fk2 FOREIGN KEY (period_period_id) REFERENCES period(period_id);
ALTER TABLE class_department ADD CONSTRAINT class_department_fk1 FOREIGN KEY (class_class_id) REFERENCES class(class_id);
ALTER TABLE class_department ADD CONSTRAINT class_department_fk2 FOREIGN KEY (department_department_id) REFERENCES department(department_id);
ALTER TABLE class_classroom ADD CONSTRAINT class_classroom_fk1 FOREIGN KEY (class_class_id) REFERENCES class(class_id);
ALTER TABLE class_classroom ADD CONSTRAINT class_classroom_fk2 FOREIGN KEY (classroom_classroom_id) REFERENCES classroom(classroom_id);