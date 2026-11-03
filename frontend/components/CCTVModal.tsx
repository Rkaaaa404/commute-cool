'use client';
import { Modal, Text, Badge, Group } from '@mantine/core';
import { useEffect, useRef } from 'react';
import Hls from 'hls.js';
import type { CCTVCamera } from '../types';

// Proxied via next.config.ts rewrites (avoids HTTP mixed-content on HTTPS deploys)
const DISHUB_HLS_BASE = '/cctv-hls';

interface Props {
  camera: CCTVCamera | null;
  onClose: () => void;
}

export default function CCTVModal({ camera, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    if (!camera || !videoRef.current) return;

    const hlsUrl = `${DISHUB_HLS_BASE}/${camera.cctv_id}/index.m3u8`;

    if (Hls.isSupported()) {
      const hls = new Hls({ maxLoadingDelay: 4, liveSyncDuration: 3 });
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoRef.current);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current?.play().catch(() => {});
      });
      hlsRef.current = hls;
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = hlsUrl;
    }

    return () => {
      hlsRef.current?.destroy();
      hlsRef.current = null;
    };
  }, [camera]);

  return (
    <Modal
      opened={!!camera}
      onClose={onClose}
      title={camera?.name || 'Live CCTV'}
      size="lg"
      centered
    >
      <div style={{ background: '#111', borderRadius: 8, overflow: 'hidden', minHeight: 240 }}>
        <video
          ref={videoRef}
          controls
          autoPlay
          muted
          playsInline
          style={{ width: '100%', display: 'block' }}
        />
      </div>
      <Group justify="space-between" mt="xs">
        {camera?.distance_m && (
          <Badge color="teal" variant="light">{Math.round(camera.distance_m)}m dari rute</Badge>
        )}
        <Text size="xs" c="dimmed">Sumber: Dishub Surabaya</Text>
      </Group>
      <Text size="xs" c="dimmed" mt="xs">
        Stream mungkin tidak tersedia jika CCTV offline atau jaringan tidak dapat mengakses server Dishub.
      </Text>
    </Modal>
  );
}
