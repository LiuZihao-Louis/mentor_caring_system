def login(client, account, password):
    return client.post('/login', data={'account': account, 'password': password}, follow_redirects=False)


def api_login(client, account, password):
    return client.post('/api/auth/login', json={'account': account, 'password': password})


def test_api_login_success_and_failure(client):
    ok = client.post('/api/auth/login', json={'account': 'admin', 'password': 'admin123'})
    assert ok.status_code == 200
    assert 'password_hash' not in ok.get_json()['user']
    fail = client.post('/api/auth/login', json={'account': 'admin', 'password': 'wrong'})
    assert fail.status_code == 403


def test_api_requires_login(client):
    r = client.get('/api/students/123456789/mentor')
    assert r.status_code == 403


def test_api_student_mentor_and_feedback(client):
    api_login(client, '123456789', 'student123')
    r = client.get('/api/students/123456789/mentor')
    assert r.status_code == 200
    assert r.get_json()['mentor_id'] == 'MTR001'
    f = client.post('/api/students/123456789/feedback', json={'content': 'Great'})
    assert f.status_code == 201


def test_api_messages_and_records(client):
    api_login(client, '123456789', 'student123')
    msg = client.post('/api/messages', json={'receiver_ids': ['MTR001'], 'content': 'Hello'})
    assert msg.status_code == 201
    assert msg.get_json()['sender_id'] == '123456789'
    client.post('/api/auth/logout')
    api_login(client, 'mary', 'mentor123')
    rec = client.post('/api/mentors/MTR001/records', json={
        'student_id': '123456789', 'date': '2026-04-01', 'time': '10:00',
        'problem_statement': 'Problem', 'interview_summary': 'Summary'
    })
    assert rec.status_code == 201


def test_api_import_students(client):
    api_login(client, 'alice', 'consultant123')
    r = client.post('/api/faculty-consultants/FC001/students/import', json={
        'academic_year': '2024-2025',
        'rows': [{
            'Student ID': '222222222', 'Student Name': 'Amy', 'Major': 'CST', 'Status': 'normal',
            'Group ID': '2024-2025-Y2', 'Mentor': 'Mary Lee', 'Office': 'T1-102', 'Mentor Email': 'marylee@bnbu.edu.cn'
        }]
    })
    assert r.status_code == 201
    assert r.get_json()['students_created'] == 1


def test_frontend_login_page_loads(client):
    r = client.get('/login')
    assert r.status_code == 200
    assert b'Login' in r.data


def test_valid_login_redirects_to_role_dashboard(client):
    r = login(client, '123456789', 'student123')
    assert r.status_code == 302
    assert '/student/dashboard' in r.headers['Location']


def test_invalid_login_shows_error(client):
    r = client.post('/login', data={'account': '123456789', 'password': 'bad'}, follow_redirects=True)
    assert r.status_code == 200
    assert b'Invalid account or password' in r.data


def test_role_dashboards_load(client):
    accounts = [
        ('123456789', 'student123', '/student/dashboard', b'Student Dashboard'),
        ('mary', 'mentor123', '/mentor/dashboard', b'Mentor Dashboard'),
        ('alice', 'consultant123', '/faculty-consultant/dashboard', b'Faculty Consultant Dashboard'),
        ('admin', 'admin123', '/admin/dashboard', b'Administrator Dashboard'),
        ('sam', 'staff123', '/supporting-staff/dashboard', b'Supporting Staff Dashboard'),
    ]
    for account, password, path, expected in accounts:
        with client:
            client.get('/logout')
            login(client, account, password)
            r = client.get(path)
            assert r.status_code == 200
            assert expected in r.data


def test_search_student_info_pages(client):
    with client:
        login(client, 'mary', 'mentor123')
        r = client.get('/mentor/student-search?student_id=123456789')
        assert r.status_code == 200
        assert b'Search Student Information' in r.data
        assert b'Bnbuer' in r.data
        assert b'Interview Records' in r.data
        assert b'Create Interview Record' in r.data

        client.get('/logout')
        login(client, 'ruth', 'coord123')
        r = client.get('/coordinator/student-search?student_id=123456789')
        assert r.status_code == 200
        assert b'Search Student Information' in r.data
        assert b'Bnbuer' in r.data
        assert b'Create Interview Record' not in r.data

        client.get('/logout')
        login(client, 'alice', 'consultant123')
        r = client.get('/faculty-consultant/students/search?student_id=123456789')
        assert r.status_code == 200
        assert b'Search Student Information' in r.data
        assert b'Bnbuer' in r.data


def test_unauthorized_dashboard_access_redirects(client):
    with client:
        login(client, '123456789', 'student123')
        r = client.get('/mentor/dashboard', follow_redirects=False)
        assert r.status_code == 302
        assert '/student/dashboard' in r.headers['Location']


def test_student_submit_feedback_from_frontend(client):
    with client:
        login(client, '123456789', 'student123')
        r = client.post('/student/feedback', data={'content': 'Frontend feedback'}, follow_redirects=True)
        assert r.status_code == 200
        assert b'Frontend feedback' in r.data


def test_mentor_create_record_from_frontend(client):
    with client:
        login(client, 'mary', 'mentor123')
        r = client.post('/mentor/records/create', data={
            'student_id': '123456789', 'date': '2026-05-01', 'time': '11:00',
            'problem_statement': 'Frontend problem', 'interview_summary': 'Frontend summary', 'follow_up_action': ''
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Record created' in r.data


def test_student_book_and_mentor_confirm_from_frontend(client, app):
    services = app.config['services']
    slot = services['mentor'].create_available_slots('MTR001', '123456789', '2026-05-02', '09:00', '09:30')[0]
    with client:
        login(client, '123456789', 'student123')
        r = client.post('/student/appointments/book', data={'appointment_id': slot.appointment_id}, follow_redirects=True)
        assert r.status_code == 200
        assert b'booked' in r.data
        client.get('/logout')
        login(client, 'mary', 'mentor123')
        r2 = client.post(f'/mentor/appointments/{slot.appointment_id}/confirm', data={'venue': 'T1-102'}, follow_redirects=True)
        assert r2.status_code == 200
        assert b'confirmed' in r2.data


def test_faculty_consultant_import_students_from_frontend(client):
    with client:
        login(client, 'alice', 'consultant123')
        rows = '[{"Student ID":"333333333","Student Name":"Joe","Major":"CST","Status":"normal","Group ID":"2024-2025-Y2","Mentor":"Mary Lee","Office":"T1-102","Mentor Email":"marylee@bnbu.edu.cn"}]'
        r = client.post('/faculty-consultant/students/import', data={'academic_year': '2024-2025', 'rows': rows}, follow_redirects=True)
        assert r.status_code == 200
        assert b'Students imported' in r.data


def test_word_export_page_creates_file(client):
    with client:
        login(client, 'mary', 'mentor123')
        r = client.get('/mentor/export')
        assert r.status_code == 200
        assert b'.docx' in r.data
