import { Container, Title, Text, SimpleGrid, Card, Badge, Table, Group } from '@mantine/core';

const corridors = [
  { name: 'Jl. Ahmad Yani (Wonokromo-Margorejo)', tcs: 0.20, volume: 'Sangat Tinggi', rec: 'Pohon + pelebaran trotoar' },
  { name: 'Jl. Basuki Rahmat (Tunjungan-Gub. Suryo)', tcs: 0.22, volume: 'Sangat Tinggi', rec: 'Pohon peneduh + kanopi' },
  { name: 'Jl. Pemuda (Gubeng-BG Junction)', tcs: 0.25, volume: 'Tinggi', rec: 'Pohon + shelter halte' },
  { name: 'Jl. Tunjungan (Genteng-Siola)', tcs: 0.28, volume: 'Tinggi', rec: 'Kanopi buatan' },
  { name: 'Jl. Urip Sumoharjo (Biliton-Gubeng)', tcs: 0.30, volume: 'Sedang', rec: 'Pohon peneduh' },
  { name: 'Jl. Darmo (Diponegoro-Joyoboyo)', tcs: 0.31, volume: 'Sedang', rec: 'Pohon peneduh' },
  { name: 'Jl. Kertajaya (ITS-Galaxy Mall)', tcs: 0.33, volume: 'Sedang', rec: 'Pohon + jalur hijau' },
];

function tcsColor(tcs: number) {
  if (tcs < 0.3) return 'red';
  if (tcs < 0.5) return 'orange';
  return 'green';
}

export default function DashboardPage() {
  return (
    <Container size="lg" py="md" style={{ height: '100%', overflow: 'auto' }}>
      <Title order={3} mb="md">Dashboard Kota Surabaya</Title>
      <Text size="sm" c="dimmed" mb="lg">
        Analisis kenyamanan termal jalur pejalan kaki untuk perencanaan penghijauan kota.
      </Text>

      <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">
        <Card withBorder shadow="xs" padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Total Segmen</Text>
          <Text size="xl" fw={700}>12,178</Text>
        </Card>
        <Card withBorder shadow="xs" padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Segmen Kritis (TCS &lt; 0.3)</Text>
          <Text size="xl" fw={700} c="red">3,241</Text>
        </Card>
        <Card withBorder shadow="xs" padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Rata-rata TCS Kota</Text>
          <Text size="xl" fw={700}>0.48</Text>
        </Card>
      </SimpleGrid>

      <Card withBorder shadow="xs" mb="lg">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Koridor Prioritas Penghijauan</Text>
          <Badge variant="light" color="teal">Data real dari pipeline</Badge>
        </Group>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>Koridor</Table.Th>
              <Table.Th>TCS</Table.Th>
              <Table.Th>Volume Pejalan Kaki</Table.Th>
              <Table.Th>Rekomendasi</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {corridors.map((c, i) => (
              <Table.Tr key={i}>
                <Table.Td>{i + 1}</Table.Td>
                <Table.Td fw={500}>{c.name}</Table.Td>
                <Table.Td><Badge color={tcsColor(c.tcs)} variant="light">{c.tcs.toFixed(2)}</Badge></Table.Td>
                <Table.Td>{c.volume}</Table.Td>
                <Table.Td><Text size="xs">{c.rec}</Text></Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
