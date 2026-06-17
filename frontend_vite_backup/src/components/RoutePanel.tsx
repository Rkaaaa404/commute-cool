import { Paper, Text, Badge, Group, Stack, Progress, CloseButton, Button } from '@mantine/core';
import { IconWalk, IconSun } from '@tabler/icons-react';
import type { RouteResponse, RouteResult, CCTVCamera } from '../types';
import { fetchNearbyCCTV } from '../services/api';
import { useState } from 'react';

interface Props {
  routeData: RouteResponse;
  onClose: () => void;
  onCCTVClick: (cam: CCTVCamera) => void;
}

function tcsColor(tcs: number) {
  if (tcs >= 0.7) return 'green';
  if (tcs >= 0.4) return 'orange';
  return 'red';
}

function RouteCard({ route, onCCTVClick }: { route: RouteResult; onCCTVClick: (cam: CCTVCamera) => void }) {
  const [cctvLoading, setCctvLoading] = useState(false);
  const isComfy = route.type === 'most_comfortable';

  const handleCCTV = async () => {
    if (!route.geometry.coordinates.length) return;
    setCctvLoading(true);
    const mid = route.geometry.coordinates[Math.floor(route.geometry.coordinates.length / 2)];
    const cameras = await fetchNearbyCCTV(mid[1], mid[0]);
    setCctvLoading(false);
    if (cameras.length > 0) onCCTVClick(cameras[0]);
  };

  return (
    <Paper withBorder radius="md" p="sm" mb="xs" style={isComfy ? { borderColor: 'var(--mantine-color-teal-4)' } : undefined}>
      <Group justify="space-between" mb={4}>
        <Text size="sm" fw={600}>{isComfy ? 'Ternyaman' : 'Terpendek'}</Text>
        {!route.within_heat_budget && <Badge color="red" size="xs">Melebihi Budget</Badge>}
        {isComfy && route.within_heat_budget && <Badge color="teal" size="xs">Rekomendasi</Badge>}
      </Group>

      <Group gap="md" mb={6}>
        <Text size="xs" c="dimmed">{(route.distance_m / 1000).toFixed(1)} km</Text>
        <Text size="xs" c="dimmed">{route.duration_min.toFixed(0)} min</Text>
        <Group gap={4}>
          <IconSun size={12} color="var(--mantine-color-yellow-6)" />
          <Text size="xs" c="dimmed">{route.sun_exposure_min.toFixed(0)} min sinar</Text>
        </Group>
        <Badge size="xs" color={tcsColor(route.avg_tcs)} variant="light">
          TCS {route.avg_tcs.toFixed(2)}
        </Badge>
      </Group>

      <Progress value={route.avg_tcs * 100} color={tcsColor(route.avg_tcs)} size="xs" radius="xl" />

      <Button
        fullWidth
        variant="light"
        color="dark"
        size="xs"
        mt="xs"
        leftSection={<IconWalk size={14} />}
        onClick={handleCCTV}
        loading={cctvLoading}
      >
        Lihat Kondisi Jalan
      </Button>
    </Paper>
  );
}

export default function RoutePanel({ routeData, onClose, onCCTVClick }: Props) {
  return (
    <Paper
      shadow="lg"
      radius="lg"
      p="md"
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        maxHeight: '45vh',
        overflow: 'auto',
        zIndex: 10,
        borderBottomLeftRadius: 0,
        borderBottomRightRadius: 0,
      }}
    >
      <Group justify="space-between" mb="sm">
        <Text size="sm" fw={700}>Pilih Rute</Text>
        <CloseButton size="sm" onClick={onClose} />
      </Group>

      <Stack gap="xs">
        {routeData.routes.map((route) => (
          <RouteCard key={route.type} route={route} onCCTVClick={onCCTVClick} />
        ))}
      </Stack>
    </Paper>
  );
}
