-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jul 27, 2024 at 03:44 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `hackkathon2024`
--

-- --------------------------------------------------------

--
-- Table structure for table `user_information`
--

CREATE TABLE `user_information` (
  `id` int(11) NOT NULL,
  `weight` float NOT NULL,
  `height` float NOT NULL,
  `gender` varchar(10) NOT NULL,
  `activity` varchar(50) NOT NULL,
  `goal` varchar(50) NOT NULL,
  `intensity` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_swedish_ci;

--
-- Dumping data for table `user_information`
--

INSERT INTO `user_information` (`id`, `weight`, `height`, `gender`, `activity`, `goal`, `intensity`, `created_at`) VALUES
(1, 155, 300, 'female', 'lightly active', 'lose weight', 'moderate', '2024-07-26 15:49:03'),
(2, 30, 100, 'male', 'extremely active', 'improve fitness', 'chill', '2024-07-26 16:02:42'),
(3, 180, 180, 'male', 'lightly active', 'lose weight', 'extreme', '2024-07-26 16:32:40'),
(4, 70, 165, 'male', 'moderately active', 'improve fitness', 'extreme', '2024-07-26 17:51:55'),
(5, 80, 150, 'female', 'lightly active', 'lose weight', 'very chill', '2024-07-26 18:03:10'),
(6, 150, 60, 'male', 'extremely active', 'recovery', 'intense', '2024-07-26 23:53:33'),
(7, 120, 280, 'female', 'extremely active', 'gain muscle', 'extreme', '2024-07-27 00:22:17');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `user_information`
--
ALTER TABLE `user_information`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `user_information`
--
ALTER TABLE `user_information`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
