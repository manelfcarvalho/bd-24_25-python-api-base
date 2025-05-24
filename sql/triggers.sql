-- ========================================================
-- =================== Database Triggers ===================
-- ========================================================

-- Trigger 1: Automatically update student's mean when grades change
CREATE OR REPLACE FUNCTION update_student_mean()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE student
    SET mean = (
        SELECT AVG(score)
        FROM result
        WHERE student_person_person_id = NEW.student_person_person_id
    )
    WHERE person_person_id = NEW.student_person_person_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mean
AFTER INSERT OR UPDATE ON result
FOR EACH ROW
EXECUTE FUNCTION update_student_mean();

-- Trigger 2: Update payment status when fees are fully paid
CREATE OR REPLACE FUNCTION update_payment_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Update major_info payment status
    UPDATE major_info
    SET status = 'Paid'
    WHERE fees_account_fees_account_id = NEW.fees_account_id
    AND fees <= NEW.values_acumulate;

    -- Update extraactivities_fees payment status
    UPDATE extraactivities_fees
    SET status = 'Paid'
    WHERE fees_account_fees_account_id = NEW.fees_account_id
    AND fees <= NEW.values_acumulate;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_payment_status
AFTER UPDATE ON fees_account
FOR EACH ROW
EXECUTE FUNCTION update_payment_status();

-- Trigger 3: Prevent enrollment when course capacity is reached
CREATE OR REPLACE FUNCTION check_course_capacity()
RETURNS TRIGGER AS $$
DECLARE
    current_count INTEGER;
    max_capacity INTEGER;
BEGIN
    -- Get the course's maximum capacity
    SELECT e.capacity INTO max_capacity
    FROM edition e
    WHERE e.course_course_id = NEW.course_course_id;

    -- Count current number of enrolled students
    SELECT COUNT(*) INTO current_count
    FROM student_course
    WHERE course_course_id = NEW.course_course_id;

    -- Check if capacity would be exceeded
    IF current_count >= max_capacity THEN
        RAISE EXCEPTION 'Course capacity exceeded. Maximum capacity is %', max_capacity;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_capacity
BEFORE INSERT ON student_course
FOR EACH ROW
EXECUTE FUNCTION check_course_capacity(); 