from mentor_caring.services.auth_service import AuthService
from mentor_caring.services.student_service import StudentService
from mentor_caring.services.mentor_service import MentorService
from mentor_caring.services.appointment_service import AppointmentService
from mentor_caring.services.message_service import MessageService
from mentor_caring.services.faculty_consultant_service import FacultyConsultantService
from mentor_caring.services.admin_service import AdministratorService
from mentor_caring.services.coordinator_service import MCPCoordinatorService
from mentor_caring.services.supporting_staff_service import SupportingStaffService
from mentor_caring.services.feedback_service import FeedbackService


def build_services(store):
    return {
        "auth": AuthService(store),
        "student": StudentService(store),
        "mentor": MentorService(store),
        "appointment": AppointmentService(store),
        "message": MessageService(store),
        "feedback": FeedbackService(store),
        "faculty_consultant": FacultyConsultantService(store),
        "admin": AdministratorService(store),
        "coordinator": MCPCoordinatorService(store),
        "supporting_staff": SupportingStaffService(store),
    }
