CREATE TABLE IF NOT EXISTS `event_participants` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'the id of this participant row',
  `event_id` int(11) NOT NULL COMMENT 'reference to the event',
  `email` varchar(100) NOT NULL COMMENT 'email of the participant (guest or owner)',
  PRIMARY KEY (`id`),
  FOREIGN KEY (`event_id`) REFERENCES `events`(`event_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT="Links users to events as participants";
