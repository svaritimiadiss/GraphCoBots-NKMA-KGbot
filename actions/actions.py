from rasa_sdk import Tracker, Action
from rasa_sdk.executor import CollectingDispatcher
from typing import Dict, Text, Any, List
from rasa_sdk.events import SlotSet, ReminderScheduled, AllSlotsReset
from neo4j import GraphDatabase
import datetime
import random
from thefuzz import process  # Import the necessary module from thefuzz
import re
from actions import utils
import yaml
import os
from dotenv import load_dotenv, set_key


# def print_friends(tx, name):
#     names = []
#     for record in tx.run("MATCH (a:WRITER)-[:MARRIEDTO]->(friend:WRITER) WHERE a.name = $name "
#                          "RETURN friend.name ORDER BY friend.name", name=name):
#         print("record friend.name: {}".format(record["friend.name"]))
#         print("record: {}".format(record))
#         names.append(record["friend.name"])
#         print("names: ", names)
#
#         # return record["friend.name"]
#
#     return record["friend.name"]


def print_books_type(tx, book_type_pl):
    books_names_list = []

    # Query without ORDER BY rand()
    for record in tx.run(
            "MATCH (a:WRITER)-[:WROTE]->(book) "
            "WHERE a.name = 'Νίκος Καζαντζάκης' AND book.type_pl = $book_type_pl "
            "RETURN book.name AS name", book_type_pl=book_type_pl):
        books_names_list.append(record["name"])

    # Randomly select up to 5 books
    random_books_list = random.sample(books_names_list, min(len(books_names_list), 5))

    # Return the count and the random selection
    count_book_type_list = len(books_names_list)
    return count_book_type_list, random_books_list


# def print_halls(tx, hall_name, exhibits_collection):
#     exhibition_names_list = []
#     exhibition_url_list = []
#
#     # Check if exhibits_collection is provided
#     if exhibits_collection is not None:
#         query = (
#             "MATCH (exhibits:EXHIBIT) - [:ISLOCATEDIN] -> (hall:HALL) "
#             "WHERE hall.name = $hall_name AND exhibits.collection = $exhibits_collection "
#             "RETURN exhibits.name AS name, exhibits.url AS url"
#         )
#         params = {"hall_name": hall_name, "exhibits_collection": exhibits_collection}
#     else:
#         query = (
#             "CALL { "
#             "    MATCH (exhibits:EXHIBIT) - [:ISLOCATEDIN] -> (hall:HALL) "
#             "    WHERE hall.name = $hall_name "
#             "    RETURN exhibits.name AS name, exhibits.url AS url "
#             "    ORDER BY rand() "
#             "    LIMIT 5 "
#             "} "
#             "RETURN name, url"
#         )
#         params = {"hall_name": hall_name}
#         print("params: ", params)
#
#     for record in tx.run(query, **params):
#         exhibition_names_list.append(record["name"])
#         exhibition_url_list.append(record["url"])
#         print("exhibition_names: ", exhibition_names_list)
#         print("exhibition_url_list: ", exhibition_url_list)
#
#     return exhibition_names_list, exhibition_url_list

def print_halls(tx, hall_name, exhibits_collection):
    exhibition_names_list = []
    exhibition_url_list = []

    # Query without ORDER BY rand()
    if exhibits_collection is not None:
        query = (
            "MATCH (exhibits:EXHIBIT) - [:ISLOCATEDIN] -> (hall:HALL) "
            "WHERE hall.name = $hall_name AND exhibits.collection = $exhibits_collection "
            "RETURN exhibits.name AS name, exhibits.url AS url"
        )
        params = {"hall_name": hall_name, "exhibits_collection": exhibits_collection}
    else:
        query = (
            "MATCH (exhibits:EXHIBIT) - [:ISLOCATEDIN] -> (hall:HALL) "
            "WHERE hall.name = $hall_name "
            "RETURN exhibits.name AS name, exhibits.url AS url"
        )
        params = {"hall_name": hall_name}

    records = list(tx.run(query, **params))
    print("records list: ", records)

    # Use Python's random.sample to select 5 random records
    if records:
        sampled_records = random.sample(records, min(len(records), 5))
        for record in sampled_records:
            exhibition_names_list.append(record["name"])
            exhibition_url_list.append(record["url"])

    return exhibition_names_list, exhibition_url_list


def print_collection(tx, exhibits_collection):
    exhibition_names_list = []

    # Check if exhibits_collection is provided
    if exhibits_collection is not None:
        for record in tx.run(
                "MATCH (exhibits:EXHIBIT) - [:ISLOCATEDIN] -> (hall:HALL) "
                "WHERE exhibits.collection = $exhibits_collection "
                "RETURN exhibits.name AS name",
                exhibits_collection=exhibits_collection):
            exhibition_names_list.append(record["name"])

    # Randomly select up to 5 exhibits
    random_exhibits_list = random.sample(exhibition_names_list, min(len(exhibition_names_list), 5))

    # Return the random selection
    return random_exhibits_list


def print_collection_and_showcase(tx, exhibits_collection, exhibits_showcase):
    exhibition_names_list = []
    exhibition_url_list = []

    exhibits_showcase = int(exhibits_showcase)

    # Check if both exhibits_collection and exhibits_showcase are provided
    if exhibits_collection is not None and exhibits_showcase is not None:
        for record in tx.run(
                "MATCH (exhibits:EXHIBIT) "
                "WHERE exhibits.collection = $exhibits_collection AND exhibits.showcase = $exhibits_showcase "
                "RETURN exhibits.name AS name, exhibits.url AS url",
                exhibits_collection=exhibits_collection, exhibits_showcase=exhibits_showcase):
            exhibition_names_list.append(record["name"])
            exhibition_url_list.append(record["url"])

    # Combine names and URLs into pairs and sample up to 5 random pairs
    exhibit_pairs = list(zip(exhibition_names_list, exhibition_url_list))
    random_exhibits = random.sample(exhibit_pairs, min(len(exhibit_pairs), 5))

    # Unpack random pairs back into separate lists for names and URLs
    random_exhibition_names, random_exhibition_urls = zip(*random_exhibits) if random_exhibits else ([], [])

    return list(random_exhibition_names), list(random_exhibition_urls)


def print_floor(tx, floor):
    exhibition_names_list = []
    exhibition_url_list = []

    # Check if the floor parameter is provided
    if floor is not None:
        for record in tx.run(
                "MATCH (exhibits:EXHIBIT) - [:ISLOCATEDIN] -> (hall:HALL) "
                "WHERE hall.floor = $floor "
                "RETURN exhibits.name AS name, exhibits.url AS url",
                floor=floor):
            exhibition_names_list.append(record["name"])
            exhibition_url_list.append(record["url"])

    # Combine names and URLs into pairs and sample up to 5 random pairs
    exhibit_pairs = list(zip(exhibition_names_list, exhibition_url_list))
    random_exhibits = random.sample(exhibit_pairs, min(len(exhibit_pairs), 5))

    # Unpack random pairs back into separate lists for names and URLs
    random_exhibition_names, random_exhibition_urls = zip(*random_exhibits) if random_exhibits else ([], [])

    return list(random_exhibition_names), list(random_exhibition_urls)


# def print_complete_graph(tx, husband, has_wife, has_written):
#     for record in tx.run("MATCH (a:Person{name: $husband})-[has_written:HAS_WRITTEN{name: $has_written}]->(book:Book)"
#                          "MATCH (a:Person{name: $husband})-[has_wife:HAS_WIFE{name: $has_wife}]->(wife:Person)"
#                          "RETURN wife.name, book.name, has_wife.name, has_written.name ORDER BY book.name",
#                          husband=husband, has_wife=has_wife, has_written=has_written):
#         print("wife: {}, book: {}, has_wife: {}, has_written: {}".format(record["wife.name"], record["book.name"],
#                                                                          record["has_wife.name"],
#                                                                          record["has_written.name"]))
#     return record["wife.name"], record["book.name"], record["has_wife.name"], record["has_written.name"]


# Etsi eftiaksa to query se CYPHER
# MERGE (a:Person{name: "Νίκος Καζαντζάκης"})-[has_written:HAS_WRITTEN{name: "έγραψε"}]->(book:Book{name: "Ο Καπετάν Μιχάλης"})
# MERGE (a)-[has_wife:HAS_WIFE{name: "σύζυγο"}]->(friend:Person{name: "Ελένη Καζαντζάκη"})

# Dictionary of known entities and their corresponding functions
ENTITY_FUNCTION_MAPPING = {
    'Νίκος Καζαντζάκης': 'print_friends',
    'μυθιστορήματα': 'print_books_type',
    'ποιήματα': 'print_books_type',
    'ταξιδιωτικά': 'print_books_type',
    'θεατρικά': 'print_books_type',
    'TRAVELEDTO': 'print_location_countries',
    'φίλος': 'print_friends_type',
    'συγγενής': 'print_relatives_type',
}

# List of known book titles for fuzzy matching
KNOWN_HALLS = [
    'Βιογραφικά',
    'Θέατρο',
    'Οδύσσεια',
    'Αίθουσα προβολών',
    'Μυθιστορήματα',
    'Είσοδος',
    'Γλυπτοθήκη',
]

KNOWN_COLLECTIONS = [
    'Αυτόγραφα',
    'Προσωπικά Αντικείμενα',
    'Έργα τέχνης',
    'Έγγραφα',
    'Επιστολικό Αρχείο',
    'Έντυπα',
    'Φωτογραφικό Αρχείο',
]

KNOWN_FLOORS = [
    'Ισόγειο',
    '1ος',
    'Σκάλα'
]


def get_relationship_2_variables(slot_based_query1, slot_based_query2):
    function_to_call = None  # Initialize function_to_call

    driver = GraphDatabase.driver(url,
                                  auth=(username, password))  # Gia Docker connection

    # print("driver.verify_connectivity(): ", driver.verify_connectivity())

    def process_query(query):
        query = str(query)

        # Regex to match numbers with 1 to 3 digits
        number_pattern = re.match(r'^\d{1,3}$', query)

        if number_pattern:
            # If the query is a number (1 to 3 digits), return the corresponding function name
            # print(f"Matched a number: {query}")
            return query, 'print_collection_and_showcase'
        else:
            # print("query:", query)
            # print("type query:", type(query))

            # Fuzzy match against known halls and collections
            halls_match, halls_score = process.extractOne(query, KNOWN_HALLS)
            # print("halls_score:", halls_score)
            # print("halls_match:", halls_match)

            collection_match, collection_score = process.extractOne(query, KNOWN_COLLECTIONS)
            # print("collection_score:", collection_score)
            # print("collection_match:", collection_match)

            if halls_score >= 60:
                return halls_match, 'print_halls'
            elif collection_score >= 60:
                return collection_match, 'print_halls'  # Calling `print_halls` for collections
            else:
                print(f"Δεν βρέθηκε αντιστοίχιση για: {query}")
                return None, None

    # Process slot_based_query1
    if isinstance(slot_based_query1, list):
        slot_based_query1 = slot_based_query1[0]
        # print("slot_based_query1[0]:", slot_based_query1)
    else:
        print("The variable is not a list.")

    match1, function1 = process_query(slot_based_query1)

    # Process slot_based_query2
    if isinstance(slot_based_query2, list):
        slot_based_query2 = slot_based_query2[0]
        # print("slot_based_query2[0]:", slot_based_query2)
    else:
        print("The variable is not a list.")

    match2, function2 = process_query(slot_based_query2)

    # Determine final matches and functions
    if function1 == 'print_halls':
        # final_match = match1 if match1 else match2
        # showcase_match = match2 if match1 is None and match2 is not None else None
        final_match = match1
        showcase_match = match2
        # print("match1: ", final_match)
        # print("match2: ", showcase_match)
    else:
        final_match = match1 if match1 else match2
        showcase_match = None

    function_to_call = function1 if function1 else function2

    # print("final_match:", final_match)
    # print("showcase_match:", showcase_match)
    # print("function_to_call:", function_to_call)

    with driver.session() as session:
        if function_to_call == 'print_collection_and_showcase':
            query_exhibition_names, query_exhibition_url = session.read_transaction(
                print_collection_and_showcase, final_match, showcase_match
            )
        elif function_to_call == 'print_halls':
            query_exhibition_names, query_exhibition_url = session.read_transaction(
                print_halls, final_match, showcase_match
            )
        driver.close()
        return query_exhibition_names, query_exhibition_url


def check_collection_and_showcase(collection_match, showcase_match):
    """
    Check if both collection and showcase variables are not None and showcase is a valid 3-digit number.
    """
    if collection_match and showcase_match and re.match(r'^\d{1,3}$', showcase_match):
        return True
    return False


def process_query(query):
    query = str(query)

    # Regex to match numbers with 1 to 3 digits
    number_pattern = re.match(r'^\d{1,3}$', query)

    if number_pattern:
        # If the query is a number (1 to 3 digits), assume it is a showcase variable
        print(f"Matched a number: {query}")
        return None, query  # No collection match, only showcase match
    else:
        # print("query:", query)
        # print("type query:", type(query))

        # Fuzzy match against known collections
        collection_match, collection_score = process.extractOne(query, KNOWN_COLLECTIONS)
        # print("collection_score:", collection_score)
        # print("collection_match:", collection_match)

        if collection_score >= 60:
            return collection_match, None  # No showcase match, only collection match
        else:
            print(f"Δεν βρέθηκε αντιστοίχιση για: {query}")
            return None, None


def get_relationship_collection_with_showcase(slot_based_query1, slot_based_query2):
    driver = GraphDatabase.driver(url,
                                  auth=("neo4j", password))  # Gia Docker connection

    # Process slot_based_query1
    if isinstance(slot_based_query1, list):
        slot_based_query1 = slot_based_query1[0]
        # print("slot_based_query1[0]:", slot_based_query1)
    else:
        print("The variable is not a list.")

    collection_match1, showcase_match1 = process_query(slot_based_query1)

    # Process slot_based_query2
    if isinstance(slot_based_query2, list):
        slot_based_query2 = slot_based_query2[0]
        # print("slot_based_query2[0]:", slot_based_query2)
    else:
        print("The variable is not a list.")

    collection_match2, showcase_match2 = process_query(slot_based_query2)

    # Determine final matches and check for valid collection and showcase
    final_collection_match = collection_match1 if collection_match1 else collection_match2
    final_showcase_match = showcase_match1 if showcase_match1 else showcase_match2

    if check_collection_and_showcase(final_collection_match, final_showcase_match):
        function_to_call = 'print_collection_and_showcase'
    else:
        function_to_call = None  # or handle the case where `function_to_call` is not set

    # print("final_collection_match:", final_collection_match)
    # print("final_showcase_match:", final_showcase_match)
    # print("function_to_call:", function_to_call)

    with driver.session() as session:
        if function_to_call == 'print_collection_and_showcase':
            query_exhibition_names, query_exhibition_url = session.read_transaction(
                print_collection_and_showcase, final_collection_match, final_showcase_match
            )
            driver.close()
            return query_exhibition_names, query_exhibition_url
        else:
            # Handle the case where no valid function is determined
            driver.close()
            return [], []  # Or another appropriate response


def get_relationship_1_variable(slot_based_query):
    function_to_call = None  # Initialize function_to_call

    driver = GraphDatabase.driver(url,
                                  auth=("neo4j", password))  # Gia Docker connection
    # print("driver.verify_connectivity(): ", driver.verify_connectivity())
    #
    # print("slot_based_query: ", slot_based_query)

    if isinstance(slot_based_query, list):
        slot_based_query = slot_based_query[0]
    else:
        print("The variable is not a list.")

    # function_to_call = None  # Initialize function_to_call

    # Check if the input is a four-digit year using regex for publication year
    year_pattern = re.match(r'^\d{4}$', slot_based_query)
    if year_pattern:
        # Directly assign the function if it's a year
        function_to_call = 'print_publicationyear'
    else:
        # Use fuzzy matching to find the closest entity
        # closest_match, match_score = process.extractOne(slot_based_query, ENTITY_FUNCTION_MAPPING.keys())
        # print("match_score: ", match_score)

        # Fuzzy match against book titles
        collection_match, collection_score = process.extractOne(slot_based_query, KNOWN_COLLECTIONS)

        # Fuzzy match against book titles
        floor_match, floor_score = process.extractOne(slot_based_query, KNOWN_FLOORS)

        # if match_score >= 60 and (match_score >= floor_score or floor_score < 60):
        #     # Choose entity function if it has higher or equal score and is above the threshold
        #     slot_based_query = closest_match
        #     function_to_call = ENTITY_FUNCTION_MAPPING.get(slot_based_query)
        #     # print("function_to_call (entity): ", function_to_call)
        if collection_score >= 60:
            # Choose collection function if it has higher score and is above the threshold
            ENTITY_FUNCTION_MAPPING[slot_based_query] = 'print_collection'
            function_to_call = 'print_collection'
            slot_based_query = collection_match
            # print("function_to_call (collection): ", function_to_call)
        elif floor_score >= 60:
            # Choose book title function if it has higher score and is above the threshold
            ENTITY_FUNCTION_MAPPING[slot_based_query] = 'print_floor'
            function_to_call = 'print_floor'
            slot_based_query = floor_match
            # print("function_to_call (book title): ", function_to_call)
        else:
            # print("Δεν βρέθηκε αντιστοίχιση για: ", slot_based_query)
            return []

    # Validation logic to confirm the matched function is appropriate
    if function_to_call not in ['print_collection', 'print_floor']:
        # print(f"The function {function_to_call} may not be suitable for the query: {slot_based_query}")
        return []

    with driver.session() as session:
        if function_to_call == 'print_floor':
            # print("mpike floor!")
            query_exhibition_names, query_exhibition_url = session.read_transaction(print_floor, slot_based_query)
            driver.close()
            return query_exhibition_names, query_exhibition_url

        elif function_to_call == 'print_collection':
            # print("mpike collection!")
            query_exhibition_names = session.read_transaction(print_collection, slot_based_query)
            driver.close()
            return query_exhibition_names

        else:
            # print("Δεν έχω βάλει ακόμα query για: ", slot_based_query)
            driver.close()
            return []


def has_entity_type(entities, type):
    return any(e for e in entities if e["entity"] == type)


def extract_entity(entities, type1, graph_attr):
    # types = ["married", "wife", "kriti", "vivlio] # enallaktikos tropos diavasmatos twn entities ston parakatw elegxo!
    # p.x. if types[0] and types[1] in query_names:
    # count = 0
    query_names = []
    # Metritis Counter gia na arithmoume ta entities kai na elegxoume ama uparxoun
    for items in entities:
        query_names.append(items["entity"])
        # print(query_names)
        # count += 1
    # print("count: {}".format(count))
    # print("Ta sunolika onomata twn entities einai: {}".format(query_names))
    # print("graph_attr: ", graph_attr)
    # print("graph_attr2: ", graph_attr2)

    # Diladi an den einai empty oi listes logw aniparktwn entities
    # if not len(entities[count-2]['entity']) == 0 and not len(entities[count-1]['entity']) == 0:
    # if entities[count-2] in globals() and entities[count-1] in globals():

    # An uparxoun ta entities "married" kai "wife" dwse tin leksi "Νίκος Καζαντζάκης" gia na mpei sto slot
    # kai na psaksei to sugkekrimeno query
    # if entities[count-2]['entity'] == type1 and entities[count-1]['entity'] == type2:

    if type1 in query_names:
        return graph_attr
    # elif ...
    #     return "Κρήτη"
    else:
        return None

    # if type1 in query_names and type2 not in query_names:
    #     return graph_attr
    # elif type1 in query_names and type2 in query_names:
    #     return graph_attr, graph_attr2
    # # elif ...
    # #     return "Κρήτη"
    # else:
    #     return None

    # return [e["value"] for e in entities if e["entity"] == type][0]


class ActionHallExhibitions(Action):
    def name(self) -> Text:
        return "action_hall_exhibitions"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        entities = tracker.latest_message.get("entities")

        # has_wife1 = has_entity_type(entities, "type")
        # has_wife2 = has_entity_type(entities, 'type')

        hall = tracker.get_slot('hall')

        collection = tracker.get_slot('collection')

        # if has_wife1 or not has_wife2:
        #     return []

        if hall is None:  # Diladi an einai empty to list logw aniparktwn entities

            return [SlotSet("hall", hall)]
            # return []
        else:

            hall = extract_entity(entities, "hall", hall)

            collection = extract_entity(entities, "collection", collection)

            exhibition_names, url = get_relationship_2_variables(hall, collection)
            # print("exhibition_names: ", exhibition_names)
            # print("url: ", url)

            # books_names = extract_entity(entities, "books_names", books_names_value)
            # print("books_names: ", books_names)
            #
            # query_type2 = get_relationship(book_description)
            # print("query_type: ", query_type2)

            # query_output_complete = get_relationship(wife)
            # print("plan_type: {}".format(query_output_complete))
            # logging.debug(f"wife is {wife}")
            # logging.debug(f"wife is {query_output_complete}")

            # Πιστεύω δεν χρειάζεται να αποθηκεύεται το relation slot γιατί δεν θα αξιοποιηθεί μάλλον ως entity σε απαντήσεις
            # return [SlotSet("countries", query_countries), SlotSet("relation", relation_value)]
            return [SlotSet("hall", hall),
                    SlotSet("exhibition_names", exhibition_names),
                    SlotSet("url", url),
                    SlotSet("collection", collection)]


class ActionUtterGraphOutputHallExhibitions(Action):
    def name(self) -> Text:
        return "action_utter_graph_output_hall_exhibitions"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # hall = tracker.get_slot('hall')

        collection = tracker.get_slot('collection')

        exhibition_names = tracker.get_slot('exhibition_names')

        # Ama den uparxei timi sto slot, tote pes ston xristi na anadiatiposei
        # Ελέγχω και για άδεια λίστα γιατί μερικά slots είναι lists
        # if (exhibition_names == [None] or exhibition_names == []) and (hall is not None):
        #     dispatcher.utter_message(
        #         f"📁-> Φαίνεται ότι δεν υπάρχουν διαθέσιμα εκθέματα για την αίθουσα {hall}.")

        # Το collection είναι string ενώ το exhibition_names είναι list
        if collection is not None and None not in exhibition_names:
            dispatcher.utter_message(response="utter_hall_exhibitions_collection")
        elif collection is None and None not in exhibition_names:
            dispatcher.utter_message(response="utter_hall_exhibitions")
        else:
            dispatcher.utter_message(response="utter_rephrase")

        return [AllSlotsReset()]


class ActionCollectionExhibitions(Action):
    def name(self) -> Text:
        return "action_collection_exhibitions"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        entities = tracker.latest_message.get("entities")

        # has_wife1 = has_entity_type(entities, "type")
        # has_wife2 = has_entity_type(entities, 'type')

        collection = tracker.get_slot('collection')

        # if has_wife1 or not has_wife2:
        #     return []

        if collection is None:  # Diladi an einai empty to list logw aniparktwn entities

            return [SlotSet("collection", collection)]
            # return []
        else:

            collection = extract_entity(entities, "collection", collection)

            exhibition_names = get_relationship_1_variable(collection)
            # print("query_type1: ", exhibition_names)
            # print("query_type2:", url)

            # books_names = extract_entity(entities, "books_names", books_names_value)
            # print("books_names: ", books_names)
            #
            # query_type2 = get_relationship(book_description)
            # print("query_type: ", query_type2)

            # query_output_complete = get_relationship(wife)
            # print("plan_type: {}".format(query_output_complete))
            # logging.debug(f"wife is {wife}")
            # logging.debug(f"wife is {query_output_complete}")

            # Πιστεύω δεν χρειάζεται να αποθηκεύεται το relation slot γιατί δεν θα αξιοποιηθεί μάλλον ως entity σε απαντήσεις
            # return [SlotSet("countries", query_countries), SlotSet("relation", relation_value)]
            return [SlotSet("exhibition_names", exhibition_names),
                    SlotSet("collection", collection)]


class ActionUtterGraphOutputCollectionExhibitions(Action):
    def name(self) -> Text:
        return "action_utter_graph_output_collection_exhibitions"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        collection = tracker.get_slot('collection')

        exhibition_names = tracker.get_slot('exhibition_names')

        # Ama den uparxei timi sto slot, tote pes ston xristi na anadiatiposei
        # Ελέγχω και για άδεια λίστα γιατί μερικά slots είναι lists
        # if (exhibition_names == [None] or exhibition_names == []) and (hall is not None):
        #     dispatcher.utter_message(
        #         f"📁-> Φαίνεται ότι δεν υπάρχουν διαθέσιμα εκθέματα για την αίθουσα {hall}.")

        # Το collection είναι string ενώ το exhibition_names είναι list
        if collection is not None and None not in exhibition_names:
            dispatcher.utter_message(response="utter_collection_exhibitions")
        elif collection is not None and None in exhibition_names:
            dispatcher.utter_message(
                response="📁-> Φαίνεται ότι δεν υπάρχουν διαθέσιμα εκθέματα στη βάση δεδομένων γράφου για τη συλλογή {collection}.")
        else:
            dispatcher.utter_message(response="utter_rephrase")

        return [AllSlotsReset()]


class ActionCollectionExhibitionsAndShowcase(Action):
    def name(self) -> Text:
        return "action_collection_exhibitions_and_showcase"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        entities = tracker.latest_message.get("entities")

        # has_wife1 = has_entity_type(entities, "type")
        # has_wife2 = has_entity_type(entities, 'type')

        collection = tracker.get_slot('collection')

        showcase = tracker.get_slot('showcase')

        # if has_wife1 or not has_wife2:
        #     return []

        if collection is None or showcase is None:  # Diladi an einai empty to list logw aniparktwn entities

            return [SlotSet("collection", collection), SlotSet("showcase", showcase)]
            # return []
        else:

            collection = extract_entity(entities, "collection", collection)

            showcase = extract_entity(entities, "showcase", showcase)

            exhibition_names, url = get_relationship_collection_with_showcase(collection, showcase)
            # print("query_type1: ", exhibition_names)
            # print("query_type2:", url)

            # books_names = extract_entity(entities, "books_names", books_names_value)
            # print("books_names: ", books_names)
            #
            # query_type2 = get_relationship(book_description)
            # print("query_type: ", query_type2)

            # query_output_complete = get_relationship(wife)
            # print("plan_type: {}".format(query_output_complete))
            # logging.debug(f"wife is {wife}")
            # logging.debug(f"wife is {query_output_complete}")

            # Πιστεύω δεν χρειάζεται να αποθηκεύεται το relation slot γιατί δεν θα αξιοποιηθεί μάλλον ως entity σε απαντήσεις
            # return [SlotSet("countries", query_countries), SlotSet("relation", relation_value)]
            return [SlotSet("collection", collection),
                    SlotSet("exhibition_names", exhibition_names),
                    SlotSet("url", url),
                    SlotSet("showcase", showcase)]


class ActionUtterGraphOutputCollectionExhibitionsAndShowcase(Action):
    def name(self) -> Text:
        return "action_utter_graph_output_collection_exhibitions_and_showcase"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        collection = tracker.get_slot('collection')

        showcase = tracker.get_slot('showcase')

        exhibition_names = tracker.get_slot('exhibition_names')

        # Ama den uparxei timi sto slot, tote pes ston xristi na anadiatiposei
        # Ελέγχω και για άδεια λίστα γιατί μερικά slots είναι lists
        # if (exhibition_names == [None] or exhibition_names == []) and (hall is not None):
        #     dispatcher.utter_message(
        #         f"📁-> Φαίνεται ότι δεν υπάρχουν διαθέσιμα εκθέματα για την αίθουσα {hall}.")

        # Το collection είναι string ενώ το exhibition_names είναι list
        if (collection is not None and showcase is not None) and exhibition_names is not []:
            dispatcher.utter_message(response="utter_collection_exhibitions_and_showcase")
        elif (collection is not None and showcase is not None) and exhibition_names is []:
            dispatcher.utter_message(
                response="📁-> Φαίνεται ότι δεν υπάρχουν διαθέσιμα εκθέματα στη βάση δεδομένων γράφου από τη συλλογή {collection} με αριθμό {showcase}.")
        else:
            dispatcher.utter_message(response="utter_rephrase")

        return [AllSlotsReset()]


class ActionFloorExhibits(Action):
    def name(self) -> Text:
        return "action_floor_exhibits"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        entities = tracker.latest_message.get("entities")

        # has_wife1 = has_entity_type(entities, "type")
        # has_wife2 = has_entity_type(entities, 'type')

        floor = tracker.get_slot('floor')

        # if has_wife1 or not has_wife2:
        #     return []

        if floor is None:  # Diladi an einai empty to list logw aniparktwn entities

            return [SlotSet("floor", floor)]
            # return []
        else:

            floor = extract_entity(entities, "floor", floor)

            exhibition_names, url = get_relationship_1_variable(floor)
            # print("query_type1: ", exhibition_names)
            # print("query_type2:", url)

            # books_names = extract_entity(entities, "books_names", books_names_value)
            # print("books_names: ", books_names)
            #
            # query_type2 = get_relationship(book_description)
            # print("query_type: ", query_type2)

            # query_output_complete = get_relationship(wife)
            # print("plan_type: {}".format(query_output_complete))
            # logging.debug(f"wife is {wife}")
            # logging.debug(f"wife is {query_output_complete}")

            # Πιστεύω δεν χρειάζεται να αποθηκεύεται το relation slot γιατί δεν θα αξιοποιηθεί μάλλον ως entity σε απαντήσεις
            # return [SlotSet("countries", query_countries), SlotSet("relation", relation_value)]
            return [SlotSet("floor", floor),
                    SlotSet("exhibition_names", exhibition_names),
                    SlotSet("url", url)]


class ActionUtterGraphOutputFloorExhibits(Action):
    def name(self) -> Text:
        return "action_utter_graph_output_floor_exhibits"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        floor = tracker.get_slot('floor')

        exhibition_names = tracker.get_slot('exhibition_names')

        # Ama den uparxei timi sto slot, tote pes ston xristi na anadiatiposei
        # Ελέγχω και για άδεια λίστα γιατί μερικά slots είναι lists
        # if (exhibition_names == [None] or exhibition_names == []) and (hall is not None):
        #     dispatcher.utter_message(
        #         f"📁-> Φαίνεται ότι δεν υπάρχουν διαθέσιμα εκθέματα για την αίθουσα {hall}.")

        # Το collection είναι string ενώ το exhibition_names είναι list
        if floor is not None and None not in exhibition_names:
            dispatcher.utter_message(response="utter_floor_exhibits")
        elif floor is not None and None in exhibition_names:
            dispatcher.utter_message(
                response="📁-> Φαίνεται ότι δεν υπάρχουν διαθέσιμα εκθέματα στη βάση δεδομένων γράφου για τον όροφο {floor}.")
        else:
            dispatcher.utter_message(response="utter_rephrase")

        return [AllSlotsReset()]


class ActionSetReminder(Action):
    """Schedules a reminder, supplied with the last message's entities."""

    def name(self) -> Text:
        return "action_set_reminder"

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # dispatcher.utter_message("Θα σε υπενθυμίσω 25 δευτερόλεπτα.")

        date = datetime.datetime.now() + datetime.timedelta(seconds=240)
        # entities = tracker.latest_message.get("entities")

        reminder = ReminderScheduled(
            "EXTERNAL_reminder",
            trigger_date_time=date,
            # entities=entities,
            name="my_reminder",
            kill_on_user_message=True,  # Whether a user message before the trigger time will abort the reminder
        )

        return [reminder]


class ActionReactToReminder(Action):
    """Reminds the user with his name when idle."""

    def name(self) -> Text:
        return "action_react_to_reminder"

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        text_list = ["Μας ξέχασες!",
                     "Είσαι ακόμα εδώ; Αν όχι, σε περιμένουμε στο μουσείο!",
                     "Είμαι εδώ ακόμα, έτοιμος να ακούσω περισσότερα από εσένα!",
                     "Είμαι εδώ ακόμα, έλα να συνεχίσουμε την κουβέντα μας!",
                     "Αν υπάρχει κάτι που θέλεις να συζητήσουμε, είμαι εδώ για να σε βοηθήσω!"]

        random_text = random.choice(text_list)

        dispatcher.utter_message(random_text)

        return []


class ActionCreateCollectionsCarousels(Action):
    def name(self) -> Text:
        return "action_create_collections_carousels"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            text='Καλώς ήρθατε στον ψηφιακό βοηθό για τις συλλογές και τα εκθέματα του μουσείου "Νίκος Καζαντζάκης". Ονομάζομαι Exhibit και θα σας παρουσιάσω τα πιο εμβληματικά εκθέματα του μουσείου. Ένας έξυπνος γράφος γνώσης είναι συνδεδεμένος με τον Exhibit για την παροχή πιο εξειδικευμένων πληροφοριών σχετικά με τα εκθέματα του μουσείου.')

        # Τα keys για το json υπάρχουν στο παρακάτω link
        # https://github.com/botfront/rasa-webchat/blob/010c0539a6c57c426d090c7c8c1ca768ec6c81dc/src/components/Widget/components/Conversation/components/Messages/components/Carousel/index.js
        message = {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": [
                    {
                        "title": "Βιογραφικά στοιχεία",
                        "subtitle": "Παιδικά χρόνια, Σύζυγοι, Φίλοι, Προσωπικά αντικείμενα",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/βιογραφικά-στοιχεία.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/viografika_stoixeia",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "Εκθέματα αίθουσας Βιογραφικά",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Η 'Οδύσεια'",
                        "subtitle": "Μεγαλόπνοο έπος του Καζαντζάκη",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/οδύσσεια.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/odusseia",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "Εκθέματα αίθουσας Οδύσσεια",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Επιρροές",
                        "subtitle": "Επιστολές & Προσωρινά εκθέματα ",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/φιλοι-κ-επιρροες-1024x681-1.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/filoi_epirroes",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Πρώιμα έργα",
                        "subtitle": "Θεατρικά, Παιδικά βιβλία και η 'Ασκητική'",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/πρώιμα-θεατρικά-εργα.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/proima_theatrika",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "ευρήματα από Θέατρο",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Μυθιστορήματα",
                        "subtitle": "'Ταξιδεύοντας...', Αναγνωστήριο, Σινεμά, Πολιτική και μελέτες για τον Καζαντζάκη",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/μυθιστορηματα-1024x511-1.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/mithistorimata",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "Ποια εκθεματα έχει η αίθουσα Μυθιστορήματα",
                                "type": "postback"
                            },
                        ]
                    }
                ]
            }
        }

        dispatcher.utter_message(attachment=message)

        return []


class ActionThematikesGeneral(Action):
    def name(self) -> Text:
        return "action_thematikes_general"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            text='Στη Μόνιμη Έκθεση, οι επισκέπτες έχουν την ευκαιρία να εξοικειωθούν με την προσωπικότητα του συγγραφέα μέσα από τις επιστολές και τα ημερολόγιά του, από προσωπικά αντικείμενα και ενθύμια των ταξιδιών του, από δυσεύρετες φωτογραφίες, από μακέτες σκηνικών και κοστουμιών, από παραστάσεις έργων του, από σπάνιο οπτικοακουστικό υλικό, καθώς και από έργα τέχνης εμπνευσμένα από τον λογοτεχνικό του κόσμο. \n \n Το φυσικό υλικό, μαζί με ψηφιακές αναπαραγωγές, αναπτύσσεται σε πέντε θεματικές ενότητες: 1) Ο άνθρωπος Καζαντζάκης - Βιογραφικά, 2) Η «Οδύσεια» του Καζαντζάκη, 3) Αλληλογραφία, φίλοι και επιρροές, 4) Πρώιμα και θεατρικά έργα και 5) Μυθιστορήματα και ταξιδιωτικά έργα.')

        # Τα keys για το json υπάρχουν στο παρακάτω link
        # https://github.com/botfront/rasa-webchat/blob/010c0539a6c57c426d090c7c8c1ca768ec6c81dc/src/components/Widget/components/Conversation/components/Messages/components/Carousel/index.js
        message = {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": [
                    {
                        "title": "Βιογραφικά στοιχεία",
                        "subtitle": "Παιδικά χρόνια, Σύζυγοι, Φίλοι, Προσωπικά αντικείμενα",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/βιογραφικά-στοιχεία.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/viografika_stoixeia",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "Εκθέματα αίθουσας Βιογραφικά",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Η 'Οδύσεια'",
                        "subtitle": "Μεγαλόπνοο έπος του Καζαντζάκη",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/οδύσσεια.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/odusseia",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "Εκθέματα αίθουσας Οδύσσεια",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Επιρροές",
                        "subtitle": "Επιστολές & Προσωρινά εκθέματα ",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/φιλοι-κ-επιρροες-1024x681-1.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/filoi_epirroes",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Πρώιμα έργα",
                        "subtitle": "Θεατρικά, Παιδικά βιβλία και η 'Ασκητική'",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/πρώιμα-θεατρικά-εργα.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/proima_theatrika",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "ευρήματα από Θέατρο",
                                "type": "postback"
                            },
                        ]
                    },
                    {
                        "title": "Μυθιστορήματα",
                        "subtitle": "'Ταξιδεύοντας...', Αναγνωστήριο, Σινεμά, Πολιτική και μελέτες για τον Καζαντζάκη",
                        "image_url": "https://www.memobot.eu/wp-content/uploads/2022/10/μυθιστορηματα-1024x511-1.jpg",
                        "buttons": [
                            {
                                "title": "Μάθε για την ενότητα",
                                "payload": "/mithistorimata",
                                "type": "postback"
                            },
                            {
                                "title": "Εκθέματα",
                                "payload": "Ποια εκθεματα έχει η αίθουσα Μυθιστορήματα",
                                "type": "postback"
                            },
                        ]
                    }
                ]
            }
        }

        dispatcher.utter_message(attachment=message)

        return []

class ActionGoodbye(Action):
    """Goodbyes the user with his name."""

    def name(self) -> Text:
        return "action_goodbye"

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        text_list = ["Αντίο, σε ευχαριστούμε για την επίσκεψη. 🙂",
                     "Αντίο, θα σε περιμένουμε στο Μουσείο. 🙂"]

        random_text = random.choice(text_list)

        dispatcher.utter_message(random_text)

        return []

# Load the responses from the JSON file just ONCE
with open('actions/genai_placeholders.yml', 'r', encoding='utf-8') as f:
    genai_data = yaml.safe_load(f)

load_dotenv()

#* Generative service endpoints
GENAI_BASE_URL = os.getenv("FASTAPI_APP_URL")
OPENAI_RESPONSE_ENDPOINT = os.getenv("OPENAI_RESPONSE_ENDPOINT")
CHAT_MODEL = CHAT_MODEL = genai_data["models"]["chat"]

class ActionDefaultFallback(Action):

    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_query = tracker.latest_message.get("text")
        print(user_query)
        # Call your RAG model API
        response = utils.action_openai_chat_completion(
            dispatcher,
            system_prompt=genai_data["tasks"]["fallback_prompts"]["system_prompt"],
            user_prompt=genai_data["tasks"]["fallback_prompts"]["user_prompt"].format(
                query=user_query),
            chat_model=CHAT_MODEL,
            endpoint_url=f"{GENAI_BASE_URL}/{OPENAI_RESPONSE_ENDPOINT}"
        )

        # Send the response back to the user
        dispatcher.utter_message(text=response)

        return []
