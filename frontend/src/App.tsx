
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { Radar } from './pages/Radar';
import { SignalDetail } from './pages/SignalDetail';
import { Briefing } from './pages/Briefing';
import { Audit } from './pages/Audit';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Radar />} />
          <Route path="signal" element={<SignalDetail />} />
          <Route path="briefing" element={<Briefing />} />
          <Route path="audit" element={<Audit />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
