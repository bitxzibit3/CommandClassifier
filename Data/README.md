# Raw
- generated_with_vector.csv - кажется это первая версия
- merged_with_labels.csv
- merged_with_labels_11_patterns.csv - 
- 12052022_one_cmd.csv - 6,7 и 8 Y могут содержать больше action. То есть больше экшенов могут быть с объектами.
- 12052022_some_cmd.csv - составные команды. От двух до трёх команд в одной фразе. Добавлен атрибут delayed
- one_cmd_v3_03062022.csv - 
- one_cmd_v4_05072022.csv - 
- data_v5.jsonl - для того, чтобы попробовать подход с выделением атрибутов, попросил макса сгенерировать команды с разметкой. Тут они. Сами команды возможно отличаются от v4.
- NERannontated_fixed_oldcrowd.jsonl - краудсорс команды из merged_with_labels_11_patterns размеченные на атрибуты, также некоторые поменяли целевые вектора или были удалены, тексты тоже могли меняться.
- data_v6.jsonl (zip) - большая часть взята из data_v5, удалены примеры где degshours не нулевые. Вместо них добавлены новые команды для degrees, hour_yandex, turn_around. Примеры где relation_1, self не нулевые, дополнены примерами из файлов relation1, relation2, self. + добавлены примеры на команду follow. Колонка degshours разеделена на 2 - degs, hours.
- NERannontated_fixed_oldcrowd.jsonl - старые краудсорсовые команды размечены на нёр, убраны дубликаты, плохие команды, исправлены некоторые метки и критические опечатки. Токены могут иметь несколько нёр меток, но крайне редко.

# Interim
Файл merged_with_labels_11_patterns_split.csv - команды разделены на множества (трейн, валид, тест)
 - type - колонка, указывающая источник данных (generator и new_generator - искусственные данные, crowdsource, students - нагенерировано людьми)
 - subset - подмножество (трейн, тест, валид)
 - fold - индексы фолдов. -1 - значит всегда в трейн, это для сгенерированных данных. 0-5 - номер фолда, по которому можно выбрать один из 5 кусков для того, чтобы сделать его тестом, а остальное в трейн загнать.

 - onecmd_v6_21112022_low - комбинация команд из data_v6.jsonl и NERannontated_fixed_oldcrowd.jsonl (с разделением на фолды) в формате таблицы для экспериментов с мультилейбл классификатором. Тексты команд приведены к lowercase и убраны знаки пунктуации.