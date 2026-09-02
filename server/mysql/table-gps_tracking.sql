--
-- Table structure for table `gps_tracking`
--

CREATE TABLE `gps_tracking` (
  `id` int(8) NOT NULL,
  `lat` varchar(14) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `lon` varchar(14) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `alt` varchar(10) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `acc` varchar(10) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `spd` varchar(10) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `sat` varchar(2) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `time` varchar(26) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `bat` varchar(5) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `ip` varchar(40) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `year` varchar(4) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `month` char(2) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `day` char(2) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `hour` char(2) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `minute` char(2) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `second` char(2) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `device` varchar(255) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `provider` char(10) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `direction` char(10) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `devicerpi` char(16) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `temprpi` char(10) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `loadrpi` char(11) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

--
-- Indexes for table `gps_tracking`
--
ALTER TABLE `gps_tracking`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`),
  ADD KEY `idx_devicerpi_time` (`devicerpi`,`time`);

--
-- AUTO_INCREMENT for table `gps_tracking`
--
ALTER TABLE `gps_tracking`
  MODIFY `id` int(8) NOT NULL AUTO_INCREMENT;
