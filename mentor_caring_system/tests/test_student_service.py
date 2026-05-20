import pytest
from mentor_caring.models import MCPGroup, Student


def test_get_mentor_success(services):
    info = services['student'].get_mentor_info_by_student_id('123456789')
    assert info['mentor_id'] == 'MTR001'
    assert info['office'] == 'T1-102'


def test_get_mentor_empty_student_id(services):
    with pytest.raises(ValueError):
        services['student'].get_mentor_info_by_student_id('   ')


def test_get_mentor_unknown_student_id(services):
    with pytest.raises(LookupError):
        services['student'].get_mentor_info_by_student_id('NO_SUCH')


def test_get_mentor_student_without_group(services, store):
    store.students.add('NO_GROUP', Student('NO_GROUP', 'No Group', 'n@mail', 'normal', None, 'FST', 'DCS', 'CST'))
    with pytest.raises(LookupError):
        services['student'].get_mentor_info_by_student_id('NO_GROUP')


def test_get_mentor_group_without_mentor(services, store):
    store.groups.add('NO_MENTOR_GROUP', MCPGroup('NO_MENTOR_GROUP', '2024-2025', 'Y1', None, 'CST', 'DCS', 'FST', ['123456789']))
    store.students.get('123456789').group_id = 'NO_MENTOR_GROUP'
    with pytest.raises(LookupError):
        services['student'].get_mentor_info_by_student_id('123456789')


def test_submit_feedback_success(services):
    feedback = services['student'].submit_feedback('123456789', 'Good support')
    assert feedback.student_id == '123456789'
    assert feedback.status == 'unrespond'


def test_submit_feedback_empty_content(services):
    with pytest.raises(ValueError):
        services['student'].submit_feedback('123456789', '   ')


def test_submit_feedback_500_characters_success(services):
    feedback = services['student'].submit_feedback('123456789', 'a' * 500)
    assert len(feedback.content) == 500


def test_submit_feedback_501_characters_fails(services):
    with pytest.raises(ValueError):
        services['student'].submit_feedback('123456789', 'a' * 501)


def test_get_feedback_by_student(services):
    services['student'].submit_feedback('123456789', 'First')
    feedback = services['student'].get_feedback_by_student('123456789')
    assert any(item.content == 'First' for item in feedback)


def test_student_send_message_boundary_300_success(services):
    msg = services['student'].send_message('123456789', 'MTR001', 'x' * 300)
    assert len(msg.content) == 300


def test_student_send_message_301_fails(services):
    with pytest.raises(ValueError):
        services['student'].send_message('123456789', 'MTR001', 'x' * 301)
