--
-- Table structure for table `gps_miesto`
--

CREATE TABLE `gps_miesto` (
  `id` int(11) NOT NULL,
  `lat` varchar(14) NOT NULL,
  `lon` varchar(14) NOT NULL,
  `miesto` text DEFAULT NULL,
  `status` varchar(2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

--
-- Indexes for table `gps_miesto`
--
ALTER TABLE `gps_miesto`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for table `gps_miesto`
--
ALTER TABLE `gps_miesto`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
