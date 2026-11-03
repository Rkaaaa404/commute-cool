'use client';

import { Group, Text, Tabs } from '@mantine/core';
import { IconMap, IconChartBar } from '@tabler/icons-react';
import { usePathname, useRouter } from 'next/navigation';

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  
  // Menentukan tab aktif berdasarkan URL: jika '/navigasi' berarti navigation, selain itu 'dashboard'
  const activeTab = pathname === '/navigasi' ? 'navigation' : 'dashboard';

  const handleTabChange = (value: string | null) => {
    if (value === 'navigation') {
      router.push('/navigasi');
    } else {
      router.push('/');
    }
  };

  return (
    <Group
      h={48}
      px="md"
      justify="space-between"
      style={{ borderBottom: '1px solid var(--mantine-color-gray-2)', flexShrink: 0, background: 'white', zIndex: 100 }}
    >
      <Text fw={700} size="sm" c="teal.7">Teduh</Text>
      <Tabs value={activeTab} onChange={handleTabChange} variant="pills">
        <Tabs.List>
          <Tabs.Tab value="dashboard" leftSection={<IconChartBar size={14} />}>Dashboard</Tabs.Tab>
          <Tabs.Tab value="navigation" leftSection={<IconMap size={14} />}>Navigasi</Tabs.Tab>
        </Tabs.List>
      </Tabs>
    </Group>
  );
}
