import os
import pytest


def test_mentor_can_search_own_student(services):
    data = services['mentor'].search_student_by_id('MTR001', '123456789')
    assert data['name'] == 'Bnbuer'


def test_mentor_cannot_search_other_student(services):
    with pytest.raises(PermissionError):
        services['mentor'].search_student_by_id('MTR001', '987654321')


def test_create_update_delete_record(services):
    record = services['mentor'].create_interview_record('MTR001', '123456789', '2026-02-01', '09:00', 'Problem', 'Summary', '')
    assert record.follow_up_action == 'None'
    old_updated = record.updated_at
    updated = services['mentor'].update_interview_record('MTR001', record.record_id, {'follow_up_action': 'Follow later'})
    assert updated.follow_up_action == 'Follow later'
    result = services['mentor'].delete_interview_record('MTR001', record.record_id)
    assert result['deleted'] == record.record_id


def test_create_slots_and_book_and_confirm(services):
    slots = services['mentor'].create_available_slots('MTR001', '123456789', '2026-03-01', '09:00', '10:00')
    assert len(slots) == 2
    booked = services['appointment'].book_appointment('123456789', slots[0].appointment_id)
    assert booked.status == 'booked'
    with pytest.raises(ValueError):
        services['appointment'].book_appointment('123456789', slots[0].appointment_id)
    with pytest.raises(ValueError):
        services['mentor'].confirm_appointment('MTR001', slots[0].appointment_id, '   ')
    confirmed = services['mentor'].confirm_appointment('MTR001', slots[0].appointment_id, 'T1-102')
    assert confirmed.status == 'confirmed'
    assert confirmed.venue == 'T1-102'


def test_cannot_book_appointment_for_another_student(services):
    slots = services['mentor'].create_available_slots('MTR001', '123456789', '2026-03-02', '09:00', '09:30')
    with pytest.raises(PermissionError):
        services['appointment'].book_appointment('987654321', slots[0].appointment_id)


def test_forward_special_case_creates_message(services):
    msg = services['mentor'].forward_special_case_to_coordinator('MTR001', '123456789', 'COR001', 'Needs support')
    assert msg.message_type == 'special_case'
    assert msg.receiver_ids == ['COR001']


def test_message_send_respond(services):
    msg = services['message'].send_message('123456789', ['MTR001'], 'Hello')
    assert msg.status == 'unrespond'
    reply = services['message'].respond_message('MTR001', msg.message_id, 'Received')
    assert reply.sender_id == 'MTR001'
    assert services['message'].get_inbox('MTR001')
    assert services['message'].get_sent_messages('123456789')


def test_non_receiver_cannot_respond(services):
    msg = services['message'].send_message('123456789', ['MTR001'], 'Hello')
    with pytest.raises(PermissionError):
        services['message'].respond_message('COR001', msg.message_id, 'No')


def test_message_validation(services):
    with pytest.raises(ValueError):
        services['message'].send_message('123456789', [], 'Hello')
    with pytest.raises(ValueError):
        services['message'].send_message('123456789', ['MTR001'], '   ')


def test_import_organization_no_duplicate(services, store):
    rows = [{'Faculty': 'FST', 'Department': 'DCS', 'Major': 'CST'}, {'Faculty': 'FST', 'Department': 'DCS', 'Major': 'DS'}]
    result = services['faculty_consultant'].import_organization_units(rows=rows)
    assert result['created_majors'] == 1
    assert store.majors.exists('DS')


def test_import_students_and_change_mentor_keeps_records(services, store):
    services['faculty_consultant'].import_students_and_mentors('FC001', rows=[{
        'Student ID': '111111111', 'Student Name': 'Tom', 'Major': 'CST', 'Status': 'normal',
        'Group ID': '2024-2025-Y2', 'Mentor': 'Mary Lee', 'Office': 'T1-102', 'Mentor Email': 'marylee@bnbu.edu.cn'
    }], academic_year='2024-2025')
    assert store.students.exists('111111111')
    old_record_count = len(store.records.all())
    services['faculty_consultant'].change_mentor_of_group('FC001', '2024-2025-Y2', 'MTR001')
    assert len(store.records.all()) == old_record_count


def test_add_remove_student_group_keeps_student(services, store):
    services['faculty_consultant'].add_student_to_group('FC001', '123456789', '2024-2025-Y2')
    services['faculty_consultant'].remove_student_from_group('FC001', '123456789', '2024-2025-Y2')
    assert store.students.exists('123456789')
    assert store.students.get('123456789').group_id is None


def test_consultant_cannot_access_other_faculty_student(services):
    with pytest.raises(PermissionError):
        services['faculty_consultant'].search_student_information('FC001', '987654321')


def test_export_word_file(services):
    result = services['faculty_consultant'].export_information_to_word('FC001')
    assert result['count'] >= 1
    assert os.path.exists(result['files'][0]['file_path'])


def test_coordinator_search_and_forward(services):
    students = services['coordinator'].search_students_in_department('COR001')
    assert any(s.student_id == '123456789' for s in students)
    mentors = services['coordinator'].search_mentors_in_department('COR001')
    assert any(m.mentor_id == 'MTR001' for m in mentors)
    msg = services['coordinator'].forward_special_case_to_faculty_consultant('COR001', '123456789', 'FC001', 'Please review')
    assert msg.receiver_ids == ['FC001']


def test_supporting_staff_can_view_logs_and_respond_feedback(services):
    feedback = services['student'].submit_feedback('123456789', 'Need help')
    logs = services['supporting_staff'].view_all_student_logs('STF001')
    assert logs
    responded = services['supporting_staff'].respond_feedback('STF001', feedback.feedback_id, 'Thanks')
    assert responded.status == 'respond'


def test_admin_non_admin_permission(services):
    with pytest.raises(PermissionError):
        services['admin'].add_faculty_consultant('MTR001', 'FC001', 'FST')


def test_admin_manage_organization_users_and_role_restore(services, store):
    services['admin'].add_faculty('admin', 'FBA')
    services['admin'].add_department('admin', 'FBA', 'DBA')
    services['admin'].add_major('admin', 'FBA', 'DBA', 'BBA')
    user = services['admin'].create_user(
        'admin', 'USR100', 'Una Assigned', 'usr100', 'usr100@bnbu.edu.cn',
        'unassigned_staff', 'pass123', is_staff=True, faculty_name='FBA'
    )
    assert user.role == 'unassigned_staff'
    services['admin'].add_faculty_consultant('admin', 'USR100', 'FBA')
    assert store.users.get('USR100').role == 'faculty_consultant'
    services['admin'].delete_faculty_consultant('admin', 'FBA', 'USR100')
    assert store.users.get('USR100').role == 'unassigned_staff'


def test_generic_feedback_from_non_student(services):
    feedback = services['feedback'].submit_feedback('MTR001', 'The workflow is useful')
    assert feedback.user_id == 'MTR001'
    assert feedback.student_id is None
    responded = services['supporting_staff'].respond_feedback('STF001', feedback.feedback_id, 'Noted')
    assert responded.status == 'respond'


def test_group_move_removes_student_from_previous_group(services, store):
    services['faculty_consultant'].import_students_and_mentors('FC001', rows=[{
        'Student ID': '444444444', 'Student Name': 'Move Me', 'Major': 'CST', 'Status': 'normal',
        'Group ID': '2024-2025-Y2', 'Mentor': 'Mary Lee', 'Office': 'T1-102', 'Mentor Email': 'marylee@bnbu.edu.cn'
    }], academic_year='2024-2025')
    store.groups.add('2024-2025-Y3', type(store.groups.get('2024-2025-Y2'))(
        '2024-2025-Y3', '2024-2025', 'Y3', 'MTR001', 'CST', 'DCS', 'FST', []
    ))
    services['faculty_consultant'].add_student_to_group('FC001', '444444444', '2024-2025-Y3')
    assert '444444444' not in store.groups.get('2024-2025-Y2').student_ids
    assert '444444444' in store.groups.get('2024-2025-Y3').student_ids


def test_coordinator_student_detail_scope(services):
    own = services['coordinator'].search_student_information('COR001', '123456789')
    assert own['student_id'] == '123456789'
    with pytest.raises(PermissionError):
        services['coordinator'].search_student_information('COR001', '987654321')
