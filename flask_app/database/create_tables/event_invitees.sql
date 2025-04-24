CREATE TABLE IF NOT EXISTS `event_invitees` (
  `invitee_id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'unique id for each invitee entry',
  `event_id` int(11) NOT NULL COMMENT 'the related event id',
  `email` varchar(100) NOT NULL COMMENT 'email address of the invitee',
  PRIMARY KEY (`invitee_id`),
  FOREIGN KEY (`event_id`) REFERENCES `events`(`event_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT="Contains email addresses of event invitees";