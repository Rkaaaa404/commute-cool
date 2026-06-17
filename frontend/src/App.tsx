import { useState } from 'react';
import { AppShell, Tabs } from '@mantine/core';
import { IconMap, IconChartBar } from '@tabler/icons-react';
import NavigationPage from './pages/NavigationPage';
import DashboardPage from './pages/DashboardPage';

export default function App() {
  const [activeTab, setActiveTab] = useState<string | null>('navigation');

  return (
    <AppShell padding={0} style={{ height: '100vh' }}>
      <AppShell.Header h={48} style={{ display: 'flex', alignItems: 'center', paddingInline: 16, gap: 12, borderBottom: '1px solid var(--mantine-color-gray-2)' }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--mantine-color-teal-7)' }}>COMMUTE-COOL</span>
        <Tabs value={activeTab} onChange={setActiveTab} variant="pills" style={{ marginLeft: 'auto' }}>
          <Tabs.List>
            <Tabs.Tab value="navigation" leftSection={<IconMap size={14} />}>Navigasi</Tabs.Tab>
            <Tabs.Tab value="dashboard" leftSection={<IconChartBar size={14} />}>Dashboard</Tabs.Tab>
          </Tabs.List>
        </Tabs>
      </AppShell.Header>

      <AppShell.Main style={{ height: 'calc(100vh - 48px)' }}>
        {activeTab === 'navigation' && <NavigationPage />}
        {activeTab === 'dashboard' && <DashboardPage />}
      </AppShell.Main>
    </AppShell>
  );
}
