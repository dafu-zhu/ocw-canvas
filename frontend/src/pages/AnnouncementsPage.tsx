import { AppLayout } from "../components/AppLayout";

export function AnnouncementsPage() {
  return (
    <AppLayout crumbs={[{ label: "Inbox" }]}>
      <div className="content">
        <h1 className="page-title">Announcements</h1>
        <div className="center-empty">
          No announcements yet. Graded-work and deadline notices will show up here once the homework
          system is live.
        </div>
      </div>
    </AppLayout>
  );
}
