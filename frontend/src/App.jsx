import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Analyses from './pages/Analyses';
import Report from './pages/Report';
import Jobs from './pages/Jobs';

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#141c35',
            color: '#f1f5f9',
            border: '1px solid rgba(99,102,241,0.2)',
            borderRadius: '10px',
            fontSize: '14px',
          },
          success: {
            iconTheme: { primary: '#10b981', secondary: '#141c35' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#141c35' },
          },
        }}
      />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="analyses" element={<Analyses />} />
          <Route path="analyses/:id" element={<Report />} />
          <Route path="postes" element={<Jobs />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
