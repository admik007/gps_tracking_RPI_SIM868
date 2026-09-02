--
-- Table structure for table `gps_provider`
--

CREATE TABLE `gps_provider` (
  `id` int(11) NOT NULL,
  `ip` varchar(15) NOT NULL,
  `provider` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
