'use client';

import { SegmentedControl, Text } from '@mantine/core';

interface MapLayerSwitcherProps {
  value: 'tcs' | 'temp';
  onChange: (val: 'tcs' | 'temp') => void;
}

export default function MapLayerSwitcher({ value, onChange }: MapLayerSwitcherProps) {
  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.95)',
        padding: '8px 12px',
        borderRadius: 10,
        boxShadow: '0 2px 10px rgba(0,0,0,0.15)',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        backdropFilter: 'blur(4px)',
      }}
    >
      <Text size="xs" fw={700} c="dimmed" style={{ letterSpacing: '0.05em' }}>
        LAYER PETA
      </Text>
      <SegmentedControl
        size="xs"
        value={value}
        onChange={(val) => onChange(val as 'tcs' | 'temp')}
        data={[
          { label: 'Kenyamanan (TCS)', value: 'tcs' },
          { label: 'Suhu Udara (UHI)', value: 'temp' },
        ]}
        color="teal"
      />
    </div>
  );
}
