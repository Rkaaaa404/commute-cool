'use client';
import { Paper, Text, Badge, Group, Stack, CloseButton, ActionIcon, ScrollArea, Divider } from '@mantine/core';
import { IconChevronDown, IconChevronUp, IconThermometer } from '@tabler/icons-react';
import type { RouteResponse, RouteResult, CCTVCamera, SegmentDetail } from '../types';
import { useState } from 'react';

interface Props {
  routeData: RouteResponse;
  selectedRouteType: string | null;
  onSelectRoute: (type: string) => void;
  onClose: () => void;
  onCCTVClick: (cam: CCTVCamera) => void;
}

function tcsColor(tcs: number) {
  if (tcs >= 0.7) return '#1a936f';
  if (tcs >= 0.4) return '#f4a261';
  return '#e63946';
}

function tcsBadgeColor(tcs: number) {
  if (tcs >= 0.7) return 'green';
  if (tcs >= 0.4) return 'orange';
  return 'red';
}

function SegmentItem({ seg }: { seg: SegmentDetail }) {
  return (
    <Group justify="space-between" align="center" py={6} style={{ borderBottom: '1px solid #f0f0f0' }}>
      <Group gap="xs">
        <IconThermometer size={16} color={tcsColor(seg.tcs_value)} />
        <div>
          <Text size="xs" fw={600}>Terasa {seg.apparent_temp.toFixed(1)}°C</Text>
          <Text size="xs" c="dimmed">{seg.length_m.toFixed(0)}m • {seg.surface || 'Jalan aspal'}</Text>
        </div>
      </Group>
      <Badge size="xs" variant="dot" color={seg.shade_ratio > 0.5 ? 'teal' : 'gray'}>
        {(seg.shade_ratio * 100).toFixed(0)}% Teduh
      </Badge>
    </Group>
  );
}

function RouteCard({
  route,
  budgetLimit,
  isRecommended,
  isSelected,
  onSelect,
}: {
  route: RouteResult;
  budgetLimit: number;
  isRecommended: boolean;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const isComfy = route.type === 'most_comfortable';
  const sunPct = budgetLimit > 0 ? Math.min((route.sun_exposure_min / budgetLimit) * 100, 100) : 0;

  return (
    <Paper
      withBorder
      radius="md"
      p="sm"
      mb="xs"
      style={{
        borderColor: isSelected ? '#1a936f' : '#dee2e6',
        borderWidth: isSelected ? 2 : 1,
        transition: 'all 0.2s ease',
      }}
    >
      {/* Header — klik untuk toggle */}
      <Group
        justify="space-between"
        wrap="nowrap"
        onClick={onSelect}
        style={{ cursor: 'pointer', userSelect: 'none' }}
        mb={6}
      >
        <Group gap="xs">
          <Text size="sm" fw={700}>{isComfy ? '🍃 Rute Ternyaman' : '⚡ Rute Tercepat'}</Text>
          {isRecommended && (
            <Badge color="teal" size="xs" variant="filled">Rekomendasi</Badge>
          )}
          {!route.within_heat_budget && (
            <Badge color="red" size="xs" variant="light">Melebihi Batas</Badge>
          )}
        </Group>
        <ActionIcon variant="subtle" size="sm" tabIndex={-1}>
          {isSelected ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
        </ActionIcon>
      </Group>

      {/* Stats selalu tampil */}
      <Group gap="md" mb={8}>
        <Text size="sm" fw={500}>{(route.distance_m / 1000).toFixed(2)} km</Text>
        <Text size="sm" fw={500}>{route.duration_min.toFixed(0)} mnt berjalan</Text>
        <Badge size="sm" color={tcsBadgeColor(route.avg_tcs)} variant="light">
          TCS {route.avg_tcs.toFixed(2)}
        </Badge>
      </Group>

      {/* Heat budget bar */}
      <Text size="xs" fw={600} mb={4} c="dimmed">
        Paparan sinar matahari: {route.sun_exposure_min.toFixed(0)} / {budgetLimit} mnt batas
      </Text>
      <div style={{ background: '#f1f3f5', borderRadius: 8, height: 10, overflow: 'hidden', marginBottom: 4 }}>
        <div style={{
          height: '100%',
          width: `${sunPct}%`,
          background: sunPct >= 100 ? '#e63946' : sunPct >= 70 ? '#f4a261' : '#1a936f',
          borderRadius: 8,
          transition: 'width 0.4s ease',
        }} />
      </div>

      {/* Expandable detail segmen — CSS show/hide, no Collapse */}
      {isSelected && (
        <div style={{ marginTop: 12 }}>
          <Divider mb="xs" label="Detail per Segmen Jalan" labelPosition="center" />
          <ScrollArea h={200} type="hover" offsetScrollbars>
            {route.segments.length > 0
              ? route.segments.map((seg, i) => <SegmentItem key={i} seg={seg} />)
              : <Text size="xs" c="dimmed" ta="center" mt="sm">Detail segmen belum tersedia.</Text>
            }
          </ScrollArea>
        </div>
      )}
    </Paper>
  );
}

export default function RoutePanel({ routeData, selectedRouteType, onSelectRoute, onClose, onCCTVClick }: Props) {
  const budgetLimit = routeData.heat_budget?.budget_limit_min ?? 15;
  const recommendedType = routeData.heat_budget?.recommended_route ?? 'most_comfortable';

  return (
    <Paper
      shadow="md"
      radius="lg"
      p="md"
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 10,
        background: '#fcfaf6',
        flex: 1,
        minHeight: 0
      }}
    >
      <Group justify="space-between" mb="sm" align="flex-start" wrap="nowrap">
        <div>
          <Text size="md" fw={800}>Pilih Rute Perjalanan</Text>
          <Text size="xs" c="dimmed">Klik kartu untuk melihat detail segmen jalan</Text>
        </div>
        <CloseButton size="md" onClick={onClose} variant="subtle" color="red" />
      </Group>

      <ScrollArea style={{ flex: 1 }} type="hover" offsetScrollbars>
        <Stack gap={0}>
          {routeData.routes.map((route) => (
            <RouteCard
              key={route.type}
              route={route}
              budgetLimit={budgetLimit}
              isRecommended={route.type === recommendedType}
              isSelected={selectedRouteType === route.type}
              onSelect={() => onSelectRoute(route.type)}
            />
          ))}
        </Stack>
      </ScrollArea>
    </Paper>
  );
}
