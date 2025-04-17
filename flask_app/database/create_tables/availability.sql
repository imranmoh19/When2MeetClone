CREATE TABLE IF NOT EXISTS `availability` (
  `availability_id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'unique identifier for this availability entry',
  `event_id`        int(11) NOT NULL                COMMENT 'foreign key to the associated event',
  `email`           varchar(100) NOT NULL           COMMENT 'email of the participant',
  `day`             date NOT NULL                   COMMENT 'specific date of availability',
  `hour`            int(11) NOT NULL                COMMENT 'hour of the day (0-23)',
  `status`          varchar(20) NOT NULL            COMMENT 'availability status: Available, Maybe, Unavailable',
  PRIMARY KEY (`availability_id`),
  FOREIGN KEY (`event_id`) REFERENCES `events`(`event_id`),
  FOREIGN KEY (`email`) REFERENCES `users`(`email`) 
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT="Tracks participant availability per event, day, and hour.";
