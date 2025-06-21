# main/app.py

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2 # Import biblioteki do obsługi PostgreSQL
from psycopg2 import sql # Do bezpiecznego składania zapytań SQL
import uuid # Nadal do generowania kluczy (dla przykładu)

# Załaduj zmienne środowiskowe (dla testów lokalnych)
# W środowisku Render, te zmienne będą ustawione automatycznie z panelu serwisu.
# from dotenv import load_dotenv
# load_dotenv()

app = Flask(__name__)

# --- Konfiguracja CORS ---
# Upewnij się, że ten adres URL odpowiada URL-owi Twojego frontendu na Render.
# Zezwala na komunikację między Twoim frontendem a tym backendem.
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:8000", # Adres Twojego frontendu podczas testowania lokalnego
    "http://localhost:3000", # Jeśli testujesz lokalnie na innym porcie
    "https://cleangirl.onrender.com" # TWÓJ AKTUALNY URL FRONTENDU NA RENDER
]}})

# --- Funkcja do łączenia z bazą danych ---
def get_db_connection():
    """Ustanawia połączenie z bazą danych PostgreSQL."""
    # DATABASE_URL jest zmienną środowiskową dostarczaną przez Render dla Twojej bazy danych PostgreSQL
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    return conn

# --- Inicjalizacja bazy danych: tworzenie tabeli i dodawanie początkowych kluczy ---
def init_db():
    """
    Tworzy tabelę 'activation_keys' jeśli nie istnieje i wstawia
    przykładowe klucze aktywacyjne.
    W PRZYKŁADZIE: Te klucze byłyby wygenerowane i dystrybuowane.
    W PRODUKCJI: Ta funkcja powinna być uruchamiana tylko raz (np. jako skrypt migracji),
    a nie przy każdym uruchomieniu serwera, aby uniknąć ponownego tworzenia tabeli
    lub dodawania zduplikowanych kluczy.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Tworzenie tabeli, jeśli nie istnieje
        cur.execute("""
            CREATE TABLE IF NOT EXISTS activation_keys (
                id SERIAL PRIMARY KEY,
                key_value VARCHAR(255) UNIQUE NOT NULL,
                is_used BOOLEAN DEFAULT FALSE
            );
        """)
        conn.commit()
        print("Tabela 'activation_keys' została pomyślnie utworzona lub już istnieje.")

        # Przykładowe klucze do dodania (tylko jeśli tabela jest pusta, dla łatwego testowania)
        # W PRAWDZIWEJ APLIKACJI: Klucze generowałbyś z góry i zarządzałbyś nimi.
        initial_keys = [
            "CLEANGIRL-ABC-123",
            "CLEANGIRL-DEF-456",
            "CLEANGIRL-GHI-789",
            # Możesz dodać więcej kluczy testowych
        ]
        
        for key in initial_keys:
            try:
                cur.execute(
                    sql.SQL("INSERT INTO activation_keys (key_value, is_used) VALUES (%s, %s) ON CONFLICT (key_value) DO NOTHING;"),
                    [key, False]
                )
                conn.commit()
            except psycopg2.Error as e:
                print(f"Błąd podczas wstawiania klucza '{key}': {e}")
                conn.rollback() # Wycofaj transakcję w przypadku błędu wstawiania

        print("Przykładowe klucze aktywacyjne zostały dodane lub już istnieją.")

    except Exception as e:
        print(f"Błąd podczas inicjalizacji bazy danych: {e}")
        if conn:
            conn.rollback() # Wycofaj transakcję w przypadku błędu
    finally:
        if conn:
            conn.close()


# --- Endpoint do aktywacji klucza ---
@app.route('/activate-key', methods=['POST'])
def activate_key():
    data = request.json
    key = data.get('key')

    if not key:
        return jsonify({'success': False, 'message': 'Klucz aktywacyjny jest wymagany.'}), 400

    key = key.strip().upper() # Oczyść i ujednolić format klucza
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Sprawdź, czy klucz istnieje i czy nie został użyty
        cur.execute(
            sql.SQL("SELECT is_used FROM activation_keys WHERE key_value = %s;"),
            [key]
        )
        result = cur.fetchone()

        if result is None:
            return jsonify({'success': False, 'message': 'Nieprawidłowy klucz aktywacyjny.'}), 400

        is_used = result[0]
        if is_used:
            return jsonify({'success': False, 'message': 'Klucz aktywacyjny został już użyty.'}), 400

        # Klucz jest prawidłowy i nieużywany - aktywuj go
        cur.execute(
            sql.SQL("UPDATE activation_keys SET is_used = TRUE WHERE key_value = %s;"),
            [key]
        )
        conn.commit()
        print(f"Klucz aktywacyjny '{key}' został pomyślnie użyty w bazie danych.")

        # W PRAWDZIWEJ APLIKACJI:
        # Tutaj powiązałbyś aktywację klucza z konkretnym użytkownikiem.
        # Np. Zaktualizuj rekord użytkownika, aby oznaczyć go jako "bez reklam".
        # Potrzebowałbyś systemu uwierzytelniania użytkowników.

        return jsonify({'success': True, 'message': 'Klucz aktywacyjny został pomyślnie aktywowany! Reklamy zostały usunięte.'}), 200

    except psycopg2.Error as e:
        print(f"Błąd bazy danych podczas aktywacji klucza: {e}")
        if conn:
            conn.rollback() # Wycofaj transakcję w przypadku błędu
        return jsonify({'success': False, 'message': f'Błąd serwera bazy danych: {e}'}), 500
    except Exception as e:
        print(f"Ogólny błąd serwera podczas aktywacji klucza: {e}")
        return jsonify({'success': False, 'message': 'Wystąpił wewnętrzny błąd serwera.'}), 500
    finally:
        if conn:
            cur.close()
            conn.close()

# --- Prosty endpoint testowy ---
@app.route('/', methods=['GET'])
def home():
    return "Backend dla Generatora Porad Cleangirl (Python Flask) z kluczami aktywacyjnymi (PostgreSQL) działa!"

if __name__ == '__main__':
    # Inicjalizuj bazę danych przy starcie aplikacji
    # W PRODUKCJI, rozważ uruchamianie migracji bazy danych poza głównym procesem aplikacji,
    # aby uniknąć problemów z ponowną inicjalizacją przy każdym restarcie.
    init_db() 
    PORT = os.environ.get('PORT', 3000) # Render użyje zmiennej PORT
    app.run(debug=True, host='0.0.0.0', port=PORT)
