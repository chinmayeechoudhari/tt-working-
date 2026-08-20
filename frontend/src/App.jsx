import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import LandingScreen from './components/LandingScreen'
import TeacherForm from './components/TeacherForm.jsx'
import RoomForm from './components/RoomForm.jsx'
import ClassForm from './components/ClassForm.jsx'
import SubjectForm from './components/SubjectForm.jsx'
import TimeSlotForm from './components/TimeSlotForm.jsx'
import TeacherSubjectForm from './components/TeacherSubjectForm.jsx'
import TeacherAvailabilityForm from './components/TeacherAvailabilityForm.jsx'
import GenerateTimetable from './components/GenerateTimetable.jsx'
import TimetableGrid from './components/TimetableGrid.jsx'
import StatusDashboard from './components/StatusDashboard.jsx'
import ConstraintsPage from './pages/ConstraintsPage.jsx'
import ChatBubble from './components/ChatBubble.jsx'

export default function App() {
  const [enteredApp, setEnteredApp] = useState(false)

  return (
    <BrowserRouter>
      {!enteredApp && (
        <LandingScreen onEnter={() => setEnteredApp(true)} />
      )}

      <div style={{
        display: 'flex',
        height: '100vh',
        width: '100%',
        overflow: 'hidden',
        background: 'var(--bg-page)',
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
        opacity: enteredApp ? 1 : 0,
        transition: 'opacity 0.4s ease, background 0.3s ease',
      }}>
        <Navbar />
        <div style={{
          flex: 1,
          height: '100vh',
          overflowY: 'auto',
          overflowX: 'hidden',
          background: 'var(--bg-page)',
        }}>
          <Routes>
            <Route path="/"                      element={<StatusDashboard />} />
            <Route path="/teachers"             element={<TeacherForm />} />
            <Route path="/rooms"                element={<RoomForm />} />
            <Route path="/classes"              element={<ClassForm />} />
            <Route path="/subjects"             element={<SubjectForm />} />
            <Route path="/timeslots"            element={<TimeSlotForm />} />
            <Route path="/teacher-subjects"     element={<TeacherSubjectForm />} />
            <Route path="/teacher-availability" element={<TeacherAvailabilityForm />} />
            <Route path="/constraints"          element={<ConstraintsPage />} />
            <Route path="/generate"             element={<GenerateTimetable />} />
            <Route path="/timetable"            element={<TimetableGrid />} />
          </Routes>
        </div>
      </div>

      <ChatBubble />
    </BrowserRouter>
  )
}
