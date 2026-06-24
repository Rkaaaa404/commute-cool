'use client';

import { useState, useMemo } from 'react';
import {
  Card, Text, Badge, Group, Stack, SimpleGrid,
  Slider, SegmentedControl, Table, ThemeIcon, Tooltip,
  RingProgress, Progress,
} from '@mantine/core';
import {
  IconFlame, IconTree, IconThermometer, IconAlertTriangle,
  IconSnowflake, IconSun, IconChartLine, IconLeaf,
} from '@tabler/icons-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import type { HeatPredictionData, HeatZone } from '@/services/api';

// ── Helpers ──────────────────────────────────────────────────────────────────

function severityColor(severity: string): string {
  if (severity === 'critical') return '#e63946';
  if (severity === 'hot') return '#f4a261';
  return '#e9c46a';
}

function tcsToLabel(tcs: number): string {
  if (tcs >= 0.7) return 'Nyaman';
  if (tcs >= 0.6) return 'Cukup';
  if (tcs >= 0.5) return 'Hangat';
  if (tcs >= 0.45) return 'Panas';
  return 'Kritis';
}

function tcsToColor(tcs: number): string {
  if (tcs >= 0.7) return 'teal';
  if (tcs >= 0.6) return 'lime';
  if (tcs >= 0.5) return 'yellow';
  if (tcs >= 0.45) return 'orange';
  return 'red';
}

/** Apply an hourly factor to a baseline TCS value */
function applyHourlyFactor(baseTcs: number, hour: number, scale: number = 0.3): number {
  const FACTORS: Record<number, number> = {
    6: -0.15, 7: -0.10, 8: -0.04, 9: 0.02, 10: 0.08,
    11: 0.13, 12: 0.16, 13: 0.15, 14: 0.13, 15: 0.08,
    16: 0.02, 17: -0.03, 18: -0.08, 19: -0.11, 20: -0.13, 21: -0.14,
  };
  const factor = FACTORS[hour] ?? 0;
  return Math.max(0.1, Math.min(1.0, baseTcs - factor * scale));
}

/** Custom recharts tooltip */
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(255, 255, 255, 0.96)', border: '1px solid #e9ecef',
      borderRadius: 10, padding: '10px 14px', fontSize: 12,
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
    }}>
      <p style={{ color: '#495057', marginBottom: 4, fontWeight: 600 }}>{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color, margin: '2px 0' }}>
          {p.name}: <b>{p.value?.toFixed(3)}</b>
        </p>
      ))}
    </div>
  );
};

// ── Component Props ───────────────────────────────────────────────────────────

interface Props {
  data: HeatPredictionData;
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function HeatPredictionTab({ data }: Props) {
  const [selectedHour, setSelectedHour] = useState(new Date().getHours());
  const [scenario, setScenario] = useState<'current' | 'green' | 'cool'>('current');

  const { summary, hourly_trend, hot_zones } = data;

  // Clamp hour to 6-21 range
  const displayHour = Math.max(6, Math.min(21, selectedHour));

  // Hourly data point for the current slider position
  const currentHourData = hourly_trend.find(h => h.hour === displayHour) ?? hourly_trend[0];

  // Compute per-zone TCS at the selected hour for the selected scenario
  const zonesAtHour = useMemo<(HeatZone & { display_tcs: number; display_severity: string })[]>(() => {
    return hot_zones.map(zone => {
      const baseTcs = scenario === 'green'
        ? zone.predicted_tcs_green
        : scenario === 'cool'
          ? zone.predicted_tcs_cool
          : zone.current_tcs;
      const displayTcs = applyHourlyFactor(baseTcs, displayHour, scenario === 'current' ? 0.3 : 0.22);
      const displaySeverity = displayTcs < 0.45 ? 'critical' : displayTcs < 0.55 ? 'hot' : 'warm';
      return { ...zone, display_tcs: displayTcs, display_severity: displaySeverity };
    }).sort((a, b) => a.display_tcs - b.display_tcs);
  }, [hot_zones, scenario, displayHour]);

  // City-level TCS at current hour + scenario
  const cityTcsAtHour = scenario === 'current'
    ? currentHourData?.tcs_current ?? summary.avg_city_tcs
    : scenario === 'green'
      ? currentHourData?.tcs_green_scenario ?? summary.avg_city_tcs
      : currentHourData?.tcs_cool_scenario ?? summary.avg_city_tcs;

  const hotPct = Math.round((zonesAtHour.filter(z => z.display_tcs < 0.5).length / Math.max(zonesAtHour.length, 1)) * 100);
  const apparentTempAtHour = currentHourData?.apparent_temp ?? summary.avg_apparent_temp;

  const isPeakHeat = displayHour >= 11 && displayHour <= 14;
  const isCoolHour = displayHour < 8 || displayHour > 18;

  // Chart data — overlay scenario line
  const chartData = hourly_trend.map(h => ({
    ...h,
    selected: h.hour === displayHour ? (scenario === 'current' ? h.tcs_current : scenario === 'green' ? h.tcs_green_scenario : h.tcs_cool_scenario) : undefined,
  }));

  return (
    <Stack gap="md">
      {/* ── Slider + Scenario ─────────────────────────────────── */}
      <Card withBorder shadow="sm" p="lg" style={{
        background: 'linear-gradient(135deg, #f4fbf7 0%, #f8f9fa 100%)',
        borderColor: '#c3f2d7',
      }}>
        <Group justify="space-between" mb="sm">
          <Group gap="xs">
            <ThemeIcon size="sm" color={isPeakHeat ? 'red' : isCoolHour ? 'blue' : 'orange'} variant="light">
              {isPeakHeat ? <IconFlame size={14} /> : isCoolHour ? <IconSnowflake size={14} /> : <IconSun size={14} />}
            </ThemeIcon>
            <Text fw={700} c="dark" size="sm" component="div">
              Simulasi Jam <span style={{ color: isPeakHeat ? '#e63946' : '#228be6' }}>{`${displayHour.toString().padStart(2, '0')}:00`}</span>
              {isPeakHeat && <Badge size="xs" color="red" ml="xs">Jam Panas</Badge>}
              {isCoolHour && <Badge size="xs" color="blue" ml="xs">Jam Sejuk</Badge>}
            </Text>
          </Group>
          <SegmentedControl
            size="xs"
            value={scenario}
            onChange={(v) => setScenario(v as 'current' | 'green' | 'cool')}
            data={[
              { label: '🌆 Saat Ini', value: 'current' },
              { label: '🌿 +Pohon', value: 'green' },
              { label: '❄️ +Cooling', value: 'cool' },
            ]}
            styles={{
              root: { background: 'rgba(0,0,0,0.03)' },
              label: { fontSize: 11 },
            }}
          />
        </Group>

        <Slider
          min={6}
          max={21}
          step={1}
          value={displayHour}
          onChange={setSelectedHour}
          marks={[
            { value: 6, label: '06' },
            { value: 9, label: '09' },
            { value: 12, label: '12' },
            { value: 15, label: '15' },
            { value: 18, label: '18' },
            { value: 21, label: '21' },
          ]}
          color={isPeakHeat ? 'red' : isCoolHour ? 'blue' : 'orange'}
          styles={{
            label: { background: isPeakHeat ? '#e63946' : '#339af0', color: 'white' },
            markLabel: { color: 'var(--mantine-color-gray-6)', fontSize: 10 },
          }}
        />
      </Card>

      {/* ── Stat Cards ────────────────────────────────────────────── */}
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        {/* TCS Kota */}
        <Card withBorder shadow="xs" p="md" style={{
          background: `linear-gradient(135deg, ${cityTcsAtHour >= 0.6 ? '#ebfaf2' : cityTcsAtHour >= 0.5 ? '#fff9db' : '#fff5f5'} 0%, #ffffff 100%)`,
          borderColor: cityTcsAtHour >= 0.6 ? '#c3f2d7' : cityTcsAtHour >= 0.5 ? '#ffe066' : '#ffc9c9',
        }}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb="xs">TCS Kota (Jam Ini)</Text>
          <Group gap="xs" align="baseline">
            <Text size="xl" fw={800} c={cityTcsAtHour >= 0.6 ? 'teal.8' : cityTcsAtHour >= 0.5 ? 'orange.8' : 'red.8'}>
              {cityTcsAtHour.toFixed(3)}
            </Text>
            <Badge size="xs" color={tcsToColor(cityTcsAtHour)} variant="light">
              {tcsToLabel(cityTcsAtHour)}
            </Badge>
          </Group>
        </Card>

        {/* Suhu Terasa */}
        <Card withBorder shadow="xs" p="md" style={{
          background: 'linear-gradient(135deg, #fff9db 0%, #ffffff 100%)',
          borderColor: '#ffe066',
        }}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb="xs">Suhu Terasa</Text>
          <Group gap="xs" align="baseline">
            <Text size="xl" fw={800} c="orange.8">{apparentTempAtHour.toFixed(1)}°C</Text>
            <ThemeIcon size="xs" color="orange" variant="transparent">
              <IconThermometer size={12} />
            </ThemeIcon>
          </Group>
        </Card>

        {/* % Area Panas */}
        <Card withBorder shadow="xs" p="md" style={{
          background: 'linear-gradient(135deg, #fff5f5 0%, #ffffff 100%)',
          borderColor: '#ffc9c9',
        }}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb="xs">% Zona Panas (Top 50)</Text>
          <Group gap="xs" align="baseline">
            <Text size="xl" fw={800} c="red.8">{hotPct}%</Text>
            <Text size="xs" c="dimmed">TCS &lt; 0.5 dari Top 50</Text>
          </Group>
        </Card>

        {/* Jam Panas Puncak */}
        <Card withBorder shadow="xs" p="md" style={{
          background: 'linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)',
          borderColor: '#e9ecef',
        }}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb="xs">Puncak Panas</Text>
          <Group gap="xs" align="baseline">
            <Text size="xl" fw={800} c="gray.8">{String(summary.peak_heat_hour).padStart(2, '0')}:00</Text>
            <Text size="xs" c="dimmed">WIB</Text>
          </Group>
        </Card>
      </SimpleGrid>

      {/* ── Chart + Distribution ───────────────────────────────── */}
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        {/* Line Chart */}
        <Card withBorder shadow="sm" p="md" style={{
          background: '#ffffff',
          borderColor: '#e9ecef',
        }}>
          <Group gap="xs" mb="md">
            <ThemeIcon size="sm" color="orange" variant="light">
              <IconChartLine size={14} />
            </ThemeIcon>
            <Text fw={700} c="dark" size="sm">Tren TCS Harian Surabaya</Text>
          </Group>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey="label" tick={{ fill: '#495057', fontSize: 10 }} />
              <YAxis domain={[0.4, 0.9]} tick={{ fill: '#495057', fontSize: 10 }} />
              <ReTooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine
                x={`${displayHour.toString().padStart(2, '0')}:00`}
                stroke="#ced4da"
                strokeDasharray="4 4"
                label={{ value: '▼', fill: '#495057', fontSize: 10, position: 'top' }}
              />
              <Line
                type="monotone"
                dataKey="tcs_current"
                name="TCS Saat Ini"
                stroke="#f4a261"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#f4a261' }}
              />
              {scenario === 'green' && (
                <Line
                  type="monotone"
                  dataKey="tcs_green_scenario"
                  name="TCS + Pohon"
                  stroke="#40c057"
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  dot={false}
                />
              )}
              {scenario === 'cool' && (
                <Line
                  type="monotone"
                  dataKey="tcs_cool_scenario"
                  name="TCS + Cooling"
                  stroke="#339af0"
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  dot={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Distribution */}
        <Card withBorder shadow="sm" p="md" style={{
          background: '#ffffff',
          borderColor: '#e9ecef',
        }}>
          <Group gap="xs" mb="md">
            <ThemeIcon size="sm" color="grape" variant="light">
              <IconAlertTriangle size={14} />
            </ThemeIcon>
            <Text fw={700} c="dark" size="sm">Distribusi Kondisi Kota</Text>
          </Group>

          <Group justify="center" mb="lg">
            <RingProgress
              size={140}
              thickness={16}
              roundCaps
              sections={[
                { value: (summary.hot_segments / summary.total_segments) * 100, color: '#e63946', tooltip: `Panas: ${summary.hot_segments}` },
                { value: (summary.warm_segments / summary.total_segments) * 100, color: '#f4a261', tooltip: `Hangat: ${summary.warm_segments}` },
                { value: (summary.cool_segments / summary.total_segments) * 100, color: '#40c057', tooltip: `Nyaman: ${summary.cool_segments}` },
              ]}
              label={
                <Stack gap={0} align="center">
                  <Text fw={800} size="lg" c="dark">{summary.hot_percentage}%</Text>
                  <Text size="xs" c="dimmed">Panas</Text>
                </Stack>
              }
            />
          </Group>

          <Stack gap="xs">
            <Group justify="space-between">
              <Group gap="xs">
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#e63946' }} />
                <Text size="xs" c="dimmed">Panas (TCS &lt; 0.5)</Text>
              </Group>
              <Text size="xs" fw={600} c="red">{summary.hot_segments.toLocaleString()}</Text>
            </Group>
            <Progress value={(summary.hot_segments / summary.total_segments) * 100} color="red" size="xs" />

            <Group justify="space-between">
              <Group gap="xs">
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#f4a261' }} />
                <Text size="xs" c="dimmed">Hangat (0.5–0.65)</Text>
              </Group>
              <Text size="xs" fw={600} c="orange">{summary.warm_segments.toLocaleString()}</Text>
            </Group>
            <Progress value={(summary.warm_segments / summary.total_segments) * 100} color="orange" size="xs" />

            <Group justify="space-between">
              <Group gap="xs">
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#40c057' }} />
                <Text size="xs" c="dimmed">Nyaman (TCS &gt; 0.65)</Text>
              </Group>
              <Text size="xs" fw={600} c="teal">{summary.cool_segments.toLocaleString()}</Text>
            </Group>
            <Progress value={(summary.cool_segments / summary.total_segments) * 100} color="teal" size="xs" />
          </Stack>
        </Card>
      </SimpleGrid>

      {/* ── Hot Zones Table ────────────────────────────────────── */}
      <Card withBorder shadow="sm" p="md" style={{
        background: '#ffffff',
        borderColor: '#e9ecef',
      }}>
        <Group justify="space-between" mb="md">
          <Group gap="xs">
            <ThemeIcon size="sm" color="red" variant="light">
              <IconFlame size={14} />
            </ThemeIcon>
            <Text fw={700} c="dark" size="sm">
              Top 20 Zona Terpanas — Jam {displayHour.toString().padStart(2, '0')}:00
            </Text>
          </Group>
          <Group gap="xs">
            <Badge size="xs" color="orange" variant="light" leftSection={<IconLeaf size={10} />}>
              Prediksi dari Spark ML
            </Badge>
          </Group>
        </Group>

        <div style={{ overflowX: 'auto' }}>
          <Table striped highlightOnHover verticalSpacing="xs" styles={{
            table: { background: 'transparent' },
            thead: { background: '#f8f9fa' },
            th: { color: '#495057', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid #dee2e6' },
            td: { borderBottom: '1px solid #e9ecef', color: '#212529' },
            tr: { borderBottom: '1px solid #e9ecef' },
          }}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>#</Table.Th>
                <Table.Th>Nama Jalan</Table.Th>
                <Table.Th>TCS Sekarang</Table.Th>
                <Table.Th>TCS + Pohon</Table.Th>
                <Table.Th>TCS + Cooling</Table.Th>
                <Table.Th>Potensi Naik</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {zonesAtHour.slice(0, 20).map((zone, i) => (
                <Table.Tr key={zone.segment_id}>
                  <Table.Td>
                    <Text size="xs" c="dimmed">{i + 1}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {zone.has_shade_tree && (
                        <Tooltip label="Sudah ada pohon" position="top">
                          <ThemeIcon size="xs" color="teal" variant="transparent">
                            <IconTree size={10} />
                          </ThemeIcon>
                        </Tooltip>
                      )}
                      <Text size="xs" fw={500}>{zone.street_name}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      size="sm"
                      variant="filled"
                      style={{ background: severityColor(zone.display_severity) }}
                    >
                      {zone.display_tcs.toFixed(3)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="teal" fw={600}>{zone.predicted_tcs_green.toFixed(3)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="cyan" fw={600}>{zone.predicted_tcs_cool.toFixed(3)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      size="xs"
                      color={zone.improvement_pct > 15 ? 'teal' : zone.improvement_pct > 5 ? 'lime' : 'gray'}
                      variant="light"
                    >
                      +{zone.improvement_pct}%
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      size="xs"
                      color={zone.display_severity === 'critical' ? 'red' : zone.display_severity === 'hot' ? 'orange' : 'yellow'}
                      variant="dot"
                    >
                      {zone.display_severity === 'critical' ? 'Kritis' : zone.display_severity === 'hot' ? 'Panas' : 'Hangat'}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      </Card>
    </Stack>
  );
}
