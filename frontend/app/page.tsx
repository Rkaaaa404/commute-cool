'use client';

import { useEffect, useState } from 'react';
import { Container, Title, Text, SimpleGrid, Card, Badge, Table, Group, Loader, Tabs } from '@mantine/core';
import { IconFlame, IconTree, IconWalk } from '@tabler/icons-react';
import {
  fetchDashboardUHI,
  fetchPriorityCorridors,
  fetchWalkabilityStats,
  fetchActiveAlerts,
  fetchHeatPrediction,
} from '@/services/api';
import type { HeatPredictionData } from '@/services/api';
import { tcsToBadgeColor } from '@/components/TCSLegend';
import HeatPredictionTab from '@/components/HeatPredictionTab';

// ── Types ────────────────────────────────────────────────────────────────────

interface UHISummary {
  total_segments: number;
  critical_segments: number;
  avg_city_tcs: number;
}

interface Corridor {
  corridor_name: string;
  avg_tcs: number;
  pedestrian_volume: string;
  nearest_transit: string | null;
  recommendation: string;
  priority_score: number;
}

interface WalkabilityStats {
  total_transit_stops: number;
  reachable_within_10min: number;
  reachable_percentage: number;
  avg_tcs_city: number;
}

// ── Component ────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [summary, setSummary] = useState<UHISummary | null>(null);
  const [corridors, setCorridors] = useState<Corridor[]>([]);
  const [walkability, setWalkability] = useState<WalkabilityStats | null>(null);
  const [alerts, setAlerts] = useState<Array<{ title: string; description: string; severity: string }>>([]);
  const [heatPrediction, setHeatPrediction] = useState<HeatPredictionData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [uhiData, corrData, walkData, alertsData, heatData] = await Promise.all([
          fetchDashboardUHI(),
          fetchPriorityCorridors(),
          fetchWalkabilityStats(),
          fetchActiveAlerts(),
          fetchHeatPrediction(),
        ]);

        if (uhiData) setSummary(uhiData.summary);
        if (corrData) setCorridors(corrData.corridors || []);
        if (walkData) setWalkability(walkData);
        if (alertsData) setAlerts(alertsData);
        if (heatData) setHeatPrediction(heatData);
      } catch (err) {
        console.error('[Dashboard] Failed to load data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <Container size="lg" py="xl" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Loader color="teal" />
      </Container>
    );
  }

  return (
    <Container size="lg" py="md" style={{ height: '100%', overflow: 'auto' }}>
      <Title order={3} mb={4}>Dashboard Kota Surabaya</Title>
      <Text size="sm" c="dimmed" mb="lg">
        Data real dari pipeline Big Data — terakhir diproses oleh Apache Spark.
      </Text>

      {/* Active weather alerts */}
      {alerts.length > 0 && (
        <Card withBorder bg="red.0" p="md" mb="md" style={{ borderColor: 'var(--mantine-color-red-3)' }}>
          <Group gap="sm" align="flex-start" wrap="nowrap">
            <span style={{ fontSize: '20px', marginTop: '2px' }}>⚠️</span>
            <div>
              <Text fw={700} c="red.9" size="sm">Peringatan Cuaca Aktif BMKG (Surabaya)</Text>
              {alerts.map((alert, i) => (
                <Text size="xs" c="red.8" key={i} mt="xs">
                  • <b>{alert.title}</b>: {alert.description}
                </Text>
              ))}
            </div>
          </Group>
        </Card>
      )}

      <Tabs defaultValue="overview" variant="outline" mb="lg">
        <Tabs.List>
          <Tabs.Tab value="overview" leftSection={<IconFlame size={14} />}>Overview</Tabs.Tab>
          <Tabs.Tab value="corridors" leftSection={<IconTree size={14} />}>Koridor Prioritas</Tabs.Tab>
          <Tabs.Tab value="walkability" leftSection={<IconWalk size={14} />}>Walkability</Tabs.Tab>
          <Tabs.Tab value="heat-prediction" leftSection={<IconFlame size={14} />} style={{ color: heatPrediction ? '#f4a261' : undefined }}>🔥 Prediksi Panas</Tabs.Tab>
        </Tabs.List>

        {/* ── Overview tab ─────────────────────────────────────────────── */}
        <Tabs.Panel value="overview" pt="md">
          <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">
            <Card withBorder shadow="xs" padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Total Segmen Jalan</Text>
              <Text size="xl" fw={700}>{summary?.total_segments?.toLocaleString() || '—'}</Text>
            </Card>
            <Card withBorder shadow="xs" padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Segmen Kritis (TCS &lt; 0.4)</Text>
              <Text size="xl" fw={700} c="red">{summary?.critical_segments?.toLocaleString() || '—'}</Text>
            </Card>
            <Card withBorder shadow="xs" padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Rata-rata TCS Kota</Text>
              <Text size="xl" fw={700}>{summary?.avg_city_tcs?.toFixed(3) || '—'}</Text>
            </Card>
          </SimpleGrid>

          {walkability && (
            <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">
              <Card withBorder shadow="xs" padding="md">
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Total Halte Transit</Text>
                <Text size="xl" fw={700}>{walkability.total_transit_stops}</Text>
              </Card>
              <Card withBorder shadow="xs" padding="md">
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Halte Terjangkau Nyaman</Text>
                <Text size="xl" fw={700} c="teal">{walkability.reachable_within_10min}</Text>
              </Card>
              <Card withBorder shadow="xs" padding="md">
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Persentase Aksesibilitas</Text>
                <Text size="xl" fw={700}>{walkability.reachable_percentage.toFixed(1)}%</Text>
              </Card>
            </SimpleGrid>
          )}
        </Tabs.Panel>

        {/* ── Corridors tab ─────────────────────────────────────────────── */}
        <Tabs.Panel value="corridors" pt="md">
          <Card withBorder shadow="xs">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Koridor Prioritas Penghijauan</Text>
              <Badge variant="light" color="teal">Data real dari Spark pipeline</Badge>
            </Group>
            {corridors.length === 0 ? (
              <Text c="dimmed" size="sm">Tidak ada data koridor. Pastikan pipeline sudah berjalan.</Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>#</Table.Th>
                    <Table.Th>Koridor</Table.Th>
                    <Table.Th>TCS</Table.Th>
                    <Table.Th>Volume</Table.Th>
                    <Table.Th>Transit Terdekat</Table.Th>
                    <Table.Th>Rekomendasi</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {corridors.map((c, i) => (
                    <Table.Tr key={i}>
                      <Table.Td>{i + 1}</Table.Td>
                      <Table.Td fw={500}>{c.corridor_name}</Table.Td>
                      <Table.Td>
                        <Badge color={tcsToBadgeColor(c.avg_tcs)} variant="light">
                          {c.avg_tcs.toFixed(2)}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{c.pedestrian_volume}</Table.Td>
                      <Table.Td><Text size="xs">{c.nearest_transit || '—'}</Text></Table.Td>
                      <Table.Td><Text size="xs">{c.recommendation}</Text></Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        {/* ── Walkability tab ───────────────────────────────────────────── */}
        <Tabs.Panel value="walkability" pt="md">
          {walkability ? (
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <Card withBorder shadow="xs" padding="md">
                <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb="xs">Aksesibilitas Transit</Text>
                <Text size="sm">
                  Dari <b>{walkability.total_transit_stops}</b> halte transit di Surabaya,{' '}
                  <b>{walkability.reachable_within_10min}</b> halte ({walkability.reachable_percentage.toFixed(1)}%)
                  dapat dijangkau melalui jalur pejalan kaki dengan TCS &gt; 0.5 dalam radius 750m.
                </Text>
              </Card>
              <Card withBorder shadow="xs" padding="md">
                <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb="xs">Rata-rata Kenyamanan Kota</Text>
                <Text size="sm">
                  TCS rata-rata seluruh segmen jalan di Surabaya adalah{' '}
                  <b style={{ color: walkability.avg_tcs_city >= 0.5 ? '#1a936f' : '#e63946' }}>
                    {walkability.avg_tcs_city.toFixed(3)}
                  </b>
                  {walkability.avg_tcs_city < 0.5 ? ' (di bawah ambang nyaman)' : ' (cukup nyaman)'}
                </Text>
              </Card>
            </SimpleGrid>
          ) : (
            <Text c="dimmed">Data walkability tidak tersedia.</Text>
          )}
        </Tabs.Panel>

        {/* ── Heat Prediction tab ────────────────────────────────────────── */}
        <Tabs.Panel value="heat-prediction" pt="md">
          {heatPrediction ? (
            <HeatPredictionTab data={heatPrediction} />
          ) : (
            <Text c="dimmed">Data prediksi panas tidak tersedia. Pastikan Spark pipeline sudah berjalan.</Text>
          )}
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
