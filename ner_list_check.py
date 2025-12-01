from modules.ner_list_tool import EntityRecognizer
recognizer = EntityRecognizer()

result_file = recognizer.process_file("output_files\\night_city_atlas.md")
