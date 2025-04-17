CREATE TABLE IF NOT EXISTS `events` (
  `event_id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'the id of this event',
  `name` varchar(255) NOT NULL COMMENT 'the name of the event',
  `creator_email` varchar(100) NOT NULL COMMENT 'email of the event creator',
  `start_date` date NOT NULL COMMENT 'start date of the event',
  `end_date` date NOT NULL COMMENT 'end date of the event',
  `start_time` time NOT NULL COMMENT 'daily start time of the event',
  `end_time` time NOT NULL COMMENT 'daily end time of the event',
  PRIMARY KEY (`event_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT="Contains event information";
