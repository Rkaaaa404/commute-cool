import { useState } from 'react';
import { Tabs, Group, Text } from '@mantine/core';
import { IconMap, IconChartBar } from '@tabler/icons-react';
import NavigationPage from './pages/NavigationPage';
import DashboardPage from './pages/DashboardPage';

export default function App() {
  const [activeTab, setActiveTab] = useState<string | null>('navigation');

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Group
        h={48}
        px="md"
        justify="space-between"
        style={{ borderBottom: '1px solid var(--mantine-color-gray-2)', flexShrink: 0, background: 'white', zIndex: 100 }}
      >
        <Text fw={700} size="sm" c="teal.7">COMMUTE-COOL</Text>
        <Tabs value={activeTab} onChange={setActiveTab} variant="pills">
          <Tabs.List>
            <Tabs.Tab value="navigation" leftSection={<IconMap size={14} />}>Navigasi</Tabs.Tab>
            <Tabs.Tab value="dashboard" leftSection={<IconChartBar size={14} />}>Dashboard</Tabs.Tab>
          </Tabs.List>
        </Tabs>
      </Group>

      {/* Content */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {activeTab === 'navigation' && <NavigationPage />}
        {activeTab === 'dashboard' && <DashboardPage />}
      </div>
    </div>
  );
}
