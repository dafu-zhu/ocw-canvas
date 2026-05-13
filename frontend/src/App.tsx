import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./components/RequireAuth";
import { AnnouncementsPage } from "./pages/AnnouncementsPage";
import { AssignmentDetailPage } from "./pages/AssignmentDetailPage";
import { CalendarPage } from "./pages/CalendarPage";
import { CourseAssignmentsPage } from "./pages/CourseAssignmentsPage";
import { CourseHomePage } from "./pages/CourseHomePage";
import { CourseModulesPage } from "./pages/CourseModulesPage";
import { CoursePlaceholderPage } from "./pages/CoursePlaceholderPage";
import { CourseSyllabusPage } from "./pages/CourseSyllabusPage";
import { CourseVideosPage } from "./pages/CourseVideosPage";
import { CoursesListPage } from "./pages/CoursesListPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

function Auth({ children }: { children: ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Auth><DashboardPage /></Auth>} />
      <Route path="/courses" element={<Auth><CoursesListPage /></Auth>} />
      <Route path="/calendar" element={<Auth><CalendarPage /></Auth>} />
      <Route path="/announcements" element={<Auth><AnnouncementsPage /></Auth>} />
      <Route path="/courses/:courseId" element={<Auth><CourseHomePage /></Auth>} />
      <Route path="/courses/:courseId/syllabus" element={<Auth><CourseSyllabusPage /></Auth>} />
      <Route path="/courses/:courseId/modules" element={<Auth><CourseModulesPage /></Auth>} />
      <Route path="/courses/:courseId/videos" element={<Auth><CourseVideosPage /></Auth>} />
      <Route
        path="/courses/:courseId/assignments"
        element={<Auth><CourseAssignmentsPage /></Auth>}
      />
      <Route
        path="/courses/:courseId/assignments/:assignmentId"
        element={<Auth><AssignmentDetailPage /></Auth>}
      />
      <Route
        path="/courses/:courseId/grades"
        element={<Auth><CoursePlaceholderPage section="Grades" /></Auth>}
      />
      <Route path="/courses/:courseId/announcements" element={<Auth><AnnouncementsPage /></Auth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
