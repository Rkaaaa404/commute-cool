-- ============================================================
-- COMMUTE-COOL Seed Data: Transit Stops Surabaya
-- Sumber: OpenStreetMap + data publik Suroboyo Bus, Trans Semanggi, KAI
-- ============================================================

-- Halte Suroboyo Bus
INSERT INTO transit_stops (name, geom, stop_type, operator, route_name) VALUES
('Halte Terminal Purabaya', ST_SetSRID(ST_MakePoint(112.7526, -7.3384), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Jl. A. Yani (RSAL)', ST_SetSRID(ST_MakePoint(112.7378, -7.3215), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Wonokromo', ST_SetSRID(ST_MakePoint(112.7380, -7.3045), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Joyoboyo', ST_SetSRID(ST_MakePoint(112.7311, -7.2981), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Darmo', ST_SetSRID(ST_MakePoint(112.7310, -7.2878), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Urip Sumoharjo', ST_SetSRID(ST_MakePoint(112.7381, -7.2757), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Basuki Rahmat', ST_SetSRID(ST_MakePoint(112.7407, -7.2679), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Tunjungan', ST_SetSRID(ST_MakePoint(112.7381, -7.2611), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Gemblongan', ST_SetSRID(ST_MakePoint(112.7345, -7.2564), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Bubutan', ST_SetSRID(ST_MakePoint(112.7310, -7.2510), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Rajawali', ST_SetSRID(ST_MakePoint(112.7326, -7.2414), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali'),
('Halte Perak', ST_SetSRID(ST_MakePoint(112.7340, -7.2313), 4326), 'bus_stop', 'Suroboyo Bus', 'Purabaya - Rajawali');

-- Trans Semanggi
INSERT INTO transit_stops (name, geom, stop_type, operator, route_name) VALUES
('Halte ITS', ST_SetSRID(ST_MakePoint(112.7942, -7.2818), 4326), 'bus_stop', 'Trans Semanggi', 'Koridor 1'),
('Halte Mulyosari', ST_SetSRID(ST_MakePoint(112.7893, -7.2710), 4326), 'bus_stop', 'Trans Semanggi', 'Koridor 1'),
('Halte Kertajaya', ST_SetSRID(ST_MakePoint(112.7630, -7.2805), 4326), 'bus_stop', 'Trans Semanggi', 'Koridor 1'),
('Halte UNAIR Kampus B', ST_SetSRID(ST_MakePoint(112.7670, -7.2721), 4326), 'bus_stop', 'Trans Semanggi', 'Koridor 1'),
('Halte Dharmahusada', ST_SetSRID(ST_MakePoint(112.7680, -7.2648), 4326), 'bus_stop', 'Trans Semanggi', 'Koridor 1'),
('Halte Galaxy Mall', ST_SetSRID(ST_MakePoint(112.7700, -7.2938), 4326), 'bus_stop', 'Trans Semanggi', 'Koridor 2');

-- Stasiun Kereta Api (KAI)
INSERT INTO transit_stops (name, geom, stop_type, operator, route_name) VALUES
('Stasiun Surabaya Gubeng', ST_SetSRID(ST_MakePoint(112.7520, -7.2656), 4326), 'train_station', 'KAI', 'Jalur Utara/Selatan'),
('Stasiun Surabaya Pasar Turi', ST_SetSRID(ST_MakePoint(112.7251, -7.2485), 4326), 'train_station', 'KAI', 'Jalur Utara'),
('Stasiun Wonokromo', ST_SetSRID(ST_MakePoint(112.7380, -7.3068), 4326), 'train_station', 'KAI', 'Jalur Selatan'),
('Stasiun Surabaya Kota (Semut)', ST_SetSRID(ST_MakePoint(112.7328, -7.2394), 4326), 'train_station', 'KAI', 'Jalur Utara');

-- WiraWiri (feeder/minibus)
INSERT INTO transit_stops (name, geom, stop_type, operator, route_name) VALUES
('Halte Taman Bungkul', ST_SetSRID(ST_MakePoint(112.7395, -7.2913), 4326), 'feeder', 'WiraWiri', 'Rute Selatan'),
('Halte Siola', ST_SetSRID(ST_MakePoint(112.7377, -7.2587), 4326), 'feeder', 'WiraWiri', 'Rute Pusat'),
('Halte Balai Kota', ST_SetSRID(ST_MakePoint(112.7369, -7.2637), 4326), 'feeder', 'WiraWiri', 'Rute Pusat'),
('Halte Tugu Pahlawan', ST_SetSRID(ST_MakePoint(112.7373, -7.2460), 4326), 'feeder', 'WiraWiri', 'Rute Utara');
