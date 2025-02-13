import os
import time
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable
from datetime import datetime, timedelta


AREA = 1
TOWN = 4
PER_PAGE = 100
API_LIMIT = 2000


def get_date():
    today = datetime.today()
    month_ago = today - timedelta(days=30)
    return month_ago.strftime('%Y-%m-%d')


def get_vacancies_hh(language, page, month_ago):
    payload = {
        "text": f"{language} программист",
        "area": AREA,
        "date_from": month_ago,
        "per_page": PER_PAGE,
        "page": page
    }
    response = requests.get("https://api.hh.ru/vacancies", params=payload)
    response.raise_for_status()
    vacancies_hh = response.json()
    return vacancies_hh["found"], vacancies_hh["items"], vacancies_hh["pages"]


def get_vacancies_sj(language, api_key, page):
    headers = {
        "X-Api-App-Id": api_key}
    payload = {
        "keyword": f"{language} программист",
        "town": TOWN,
        "count": PER_PAGE,
        "page": page
    }
    response = requests.get("https://api.superjob.ru/2.0/vacancies", headers=headers, params=payload)
    response.raise_for_status()
    vacancies_sj = response.json()
    return vacancies_sj["total"], vacancies_sj["objects"], vacancies_sj["more"]


def calculate_average_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from and not salary_to:
        return salary_from * 1.2
    elif not salary_from and salary_to:
        return salary_to * 0.8
    else:
        return None


def predict_rub_salary_hh(vacancies):
    total_salary = 0
    vacancy_count = 0

    for vacancy in vacancies:
        if not vacancy["salary"]:
            continue
        if vacancy["salary"].get("currency") != "RUR":
            continue
        salary_from = vacancy["salary"].get("from")
        salary_to = vacancy["salary"].get("to")
        average_salary = calculate_average_salary(salary_from, salary_to)
        if average_salary:
            total_salary += average_salary
            vacancy_count += 1

    average_salary = 0 if not vacancy_count else total_salary / vacancy_count
    return vacancy_count, int(average_salary)


def predict_rub_salary_sj(vacancies):
    total_salary = 0
    vacancy_count = 0

    for vacancy in vacancies:
        if vacancy["currency"] != "rub":
            continue
        salary_from = vacancy["payment_from"]
        salary_to = vacancy["payment_to"]
        average_salary = calculate_average_salary(salary_from, salary_to)
        if average_salary:
            total_salary += average_salary
            vacancy_count += 1

    average_salary = 0 if not vacancy_count else total_salary / vacancy_count
    return vacancy_count, int(average_salary)


def get_languages_statistic_hh(languages, month_ago):
    languages_statistic = {}

    for language in languages:
        page = 0
        collected_vacancies = []
        vacancies_found = 0
        while True:
            try:
                vacancies_found, vacancies, pages = get_vacancies_hh(language, page, month_ago)
            except requests.exceptions.ConnectionError as e:
                print(f"Проблема с соединением, подробности: {e}")
                time.sleep(10)
                continue
            if vacancies_found and pages:
                collected_vacancies.extend(vacancies)
                page += 1
                time.sleep(1)
                if page >= pages:
                    break
        vacancies_processed, average_salary = predict_rub_salary_hh(collected_vacancies)
        languages_statistic[language] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": vacancies_processed,
            "average_salary": average_salary
        }
    sorted_languages_statistic = dict(
        sorted(
            languages_statistic.items(),
            key=lambda item: item[1]["vacancies_found"],
            reverse=True
        )
    )
    return sorted_languages_statistic


def get_languages_statistic_sj(languages, api_key):
    languages_statistic = {}

    for language in languages:
        page = 0
        collected_vacancies = []
        while True:
            vacancies_found, vacancies, vacancies_more = get_vacancies_sj(language, api_key, page)
            collected_vacancies.extend(vacancies)
            page += 1
            if page >= vacancies_more:
                break
        vacancies_processed, average_salary = predict_rub_salary_sj(collected_vacancies)
        languages_statistic[language] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": vacancies_processed,
            "average_salary": average_salary
        }
    sorted_languages_statistic = dict(
        sorted(
            languages_statistic.items(),
            key=lambda item: item[1]["vacancies_found"],
            reverse=True
        )
    )
    return sorted_languages_statistic


def create_vacancies_table(sorted_vacancy, title):

    table_data = [
        ["Язык программирования", "Найдено вакансий", "Обработано вакансий", "Средняя зарплата"]
    ]

    for language, stats in sorted_vacancy.items():
        table_data.append([
            language,
            stats["vacancies_found"],
            stats["vacancies_processed"],
            stats["average_salary"]
        ])

    table = AsciiTable(table_data)
    table.title = title
    return table.table


def main():
    load_dotenv()
    api_key = os.getenv("SJ_KEY")
    languages = ['Python', 'Java', 'JavaScript', 'C#', 'C++', 'PHP', 'Ruby', 'Go', 'Swift', 'Kotlin', 'Node.js']
    month_ago = get_date()
    print(create_vacancies_table(get_languages_statistic_hh(languages, month_ago), title="HeadHunter Moscow"))
    print(create_vacancies_table(get_languages_statistic_sj(languages, api_key), title="SuperJob Moscow"))


if __name__ == "__main__":
    main()
