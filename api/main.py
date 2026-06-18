import json
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    ORDER_STATUSES, STATUS_MAP, STATUS_NAMES, STATUS_EMOJIS, DB_PATH
)

# Путь к файлу с заказами
ORDERS_FILE = DB_PATH

app = FastAPI(title="Управление заказами")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === МОДЕЛИ ДАННЫХ ===

class OrderFieldUpdate(BaseModel):
    field: str
    value: str


class OrderStatusUpdate(BaseModel):
    status: str


# === РАБОТА С ФАЙЛОМ ===

def load_orders() -> Dict[str, List[Dict]]:
    if ORDERS_FILE.exists():
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_orders(orders: Dict[str, List[Dict]]):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def get_all_orders() -> List[Dict]:
    orders = load_orders()
    result = []
    for user_id, user_orders in orders.items():
        for order in user_orders:
            order_copy = order.copy()
            order_copy['user_id'] = user_id
            status = order_copy.get('status', 'new')
            order_copy['status_name'] = STATUS_NAMES.get(status, status)
            order_copy['status_emoji'] = STATUS_EMOJIS.get(status, '📋')
            result.append(order_copy)
    return result


def get_order_by_number(order_number: str) -> Optional[Dict]:
    orders = load_orders()
    for user_id, user_orders in orders.items():
        for order in user_orders:
            if order.get('order_number') == order_number:
                order_copy = order.copy()
                order_copy['user_id'] = user_id
                status = order_copy.get('status', 'new')
                order_copy['status_name'] = STATUS_NAMES.get(status, status)
                order_copy['status_emoji'] = STATUS_EMOJIS.get(status, '📋')
                return order_copy
    return None


def update_order_field(order_number: str, field: str, value: str) -> bool:
    orders = load_orders()
    for user_id, user_orders in orders.items():
        for order in user_orders:
            if order.get('order_number') == order_number:
                order[field] = value
                save_orders(orders)
                return True
    return False


def update_order_status(order_number: str, status: str) -> bool:
    if status not in STATUS_MAP:
        return False
    orders = load_orders()
    for user_id, user_orders in orders.items():
        for order in user_orders:
            if order.get('order_number') == order_number:
                order['status'] = status
                save_orders(orders)
                return True
    return False


def delete_order(order_number: str) -> bool:
    orders = load_orders()
    for user_id, user_orders in orders.items():
        for i, order in enumerate(user_orders):
            if order.get('order_number') == order_number:
                del user_orders[i]
                save_orders(orders)
                return True
    return False


def get_status_class(status: str) -> str:
    classes = {
        'new': 'status-new',
        'collecting': 'status-collecting',
        'ready': 'status-ready',
        'delivering': 'status-delivering',
        'delivered': 'status-delivered'
    }
    return classes.get(status, '')


# === HTML ГЕНЕРАТОРЫ ===

def render_admin_index(orders: List[Dict], error: str = None) -> str:
    """Страница админа - все заказы."""
    total = len(orders)
    stats = {}
    for s in ORDER_STATUSES:
        stats[s['id']] = sum(1 for o in orders if o.get('status') == s['id'])

    cards = ''
    for order in orders:
        status = order.get('status', 'new')
        status_class = get_status_class(status)
        status_name = STATUS_NAMES.get(status, status)
        status_emoji = STATUS_EMOJIS.get(status, '📋')
        address = order.get('address', '—')
        if len(address) > 30:
            address = address[:30] + '...'

        cards += f'''
        <a href="/admin/order/{order.get('order_number')}" class="order-card">
            <div class="order-number">📋 Заказ <span>#{order.get('order_number', '—')}</span></div>
            <div class="info">
                <div class="row">
                    <span class="label">Адрес</span>
                    <span>{address}</span>
                </div>
                <div class="row">
                    <span class="label">Телефон</span>
                    <span>{order.get('phone', '—')}</span>
                </div>
                <div class="row">
                    <span class="label">Сумма</span>
                    <span>{order.get('amount', '—')}</span>
                </div>
                <div class="row">
                    <span class="label">Статус</span>
                    <span class="status {status_class}">{status_emoji} {status_name}</span>
                </div>
            </div>
        </a>
        '''

    error_html = f'<div class="error-msg">{error}</div>' if error else ''
    no_orders_html = '''
        <div class="no-orders">
            <span class="emoji">📭</span>
            Заказов пока нет
        </div>
    ''' if not orders else ''

    stats_html = ''
    for s in ORDER_STATUSES:
        stats_html += f'''
        <div class="stat-card">
            <div class="number {s['id']}">{stats.get(s['id'], 0)}</div>
            <div class="label">{s['emoji']} {s['name']}</div>
        </div>
        '''

    return f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Админ-панель</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 28px; }}
        .header .badge {{
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            text-align: center;
        }}
        .stat-card .number {{ font-size: 32px; font-weight: bold; }}
        .stat-card .number.new {{ color: #ffc107; }}
        .stat-card .number.collecting {{ color: #007bff; }}
        .stat-card .number.ready {{ color: #28a745; }}
        .stat-card .number.delivering {{ color: #fd7e14; }}
        .stat-card .number.delivered {{ color: #6c757d; }}
        .stat-card .label {{ color: #666; font-size: 14px; }}
        .orders-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}
        .order-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
        }}
        .order-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        }}
        .order-card .order-number {{ font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px; }}
        .order-card .order-number span {{ color: #667eea; }}
        .order-card .info {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }}
        .order-card .info .row {{ display: flex; justify-content: space-between; font-size: 14px; color: #555; }}
        .order-card .info .row .label {{ color: #999; }}
        .order-card .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }}
        .status-new {{ background: #fff3cd; color: #856404; }}
        .status-collecting {{ background: #cce5ff; color: #004085; }}
        .status-ready {{ background: #d4edda; color: #155724; }}
        .status-delivering {{ background: #fff3cd; color: #856404; }}
        .status-delivered {{ background: #e2e3e5; color: #383d41; }}
        .no-orders {{ text-align: center; padding: 60px 20px; color: #999; font-size: 18px; }}
        .no-orders .emoji {{ font-size: 64px; display: block; margin-bottom: 20px; }}
        .error-msg {{
            background: #f8d7da;
            color: #721c24;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
        }}
        @media (max-width: 768px) {{
            .stats {{ grid-template-columns: repeat(3, 1fr); }}
            .orders-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>👨‍💼 Админ-панель</h1>
                <p>Управление всеми заказами</p>
            </div>
            <div class="badge">Всего: {total}</div>
        </div>

        {error_html}

        <div class="stats">
            {stats_html}
        </div>

        <div class="orders-grid">
            {cards}
        </div>
        {no_orders_html}
    </div>
</body>
</html>
    '''


def render_admin_order(order: Dict, order_number: str) -> str:
    """Страница админа - детали заказа."""
    status = order.get('status', 'new')
    status_class = get_status_class(status)
    status_name = STATUS_NAMES.get(status, status)
    status_emoji = STATUS_EMOJIS.get(status, '📋')

    # Генерация полей
    fields = [
        ('📍 Адрес', 'address', order.get('address', '—')),
        ('🕐 Время', 'time_interval', order.get('time_interval', '—')),
        ('📱 Телефон', 'phone', order.get('phone', '—')),
        ('💰 Сумма', 'amount', order.get('amount', '—')),
        ('📝 Комментарий', 'comment', order.get('comment', '—'))
    ]

    fields_html = ''
    for label, field, value in fields:
        fields_html += f'''
        <div class="field-row">
            <span class="field-label">{label}</span>
            <div class="field-value">
                <span class="text" id="display_{field}">{value}</span>
                <input type="text" id="input_{field}" value="{value}" data-field="{field}">
            </div>
        </div>
        '''

    # Кнопки статусов для админа
    status_buttons = ''
    for s in ORDER_STATUSES:
        if s['id'] != status:
            status_buttons += f'''
            <button class="btn btn-status" onclick="updateStatus('{s['id']}')">
                {s['emoji']} {s['name']}
            </button>
            '''

    return f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Заказ #{order_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            padding: 20px;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .back-btn {{
            display: inline-block;
            margin-bottom: 20px;
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .back-btn:hover {{ text-decoration: underline; }}
        .order-card {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .order-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f2f5;
        }}
        .order-header h1 {{ font-size: 24px; }}
        .order-header h1 span {{ color: #667eea; }}
        .status-badge {{
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }}
        .status-new {{ background: #fff3cd; color: #856404; }}
        .status-collecting {{ background: #cce5ff; color: #004085; }}
        .status-ready {{ background: #d4edda; color: #155724; }}
        .status-delivering {{ background: #fff3cd; color: #856404; }}
        .status-delivered {{ background: #e2e3e5; color: #383d41; }}
        .order-fields {{ display: flex; flex-direction: column; gap: 16px; margin-bottom: 30px; }}
        .field-row {{
            display: flex;
            align-items: center;
            padding: 12px 16px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .field-label {{ width: 140px; font-weight: 500; color: #555; flex-shrink: 0; }}
        .field-value {{ flex: 1; color: #333; }}
        .field-value .text {{ display: block; cursor: pointer; padding: 4px 8px; border-radius: 4px; }}
        .field-value .text:hover {{ background: #e9ecef; }}
        .field-value input {{
            width: 100%;
            padding: 6px 10px;
            border: 2px solid #667eea;
            border-radius: 6px;
            font-size: 14px;
            display: none;
        }}
        .field-value input.active {{ display: block; }}
        .field-value .text.hidden {{ display: none; }}
        .actions {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            padding-top: 20px;
            border-top: 2px solid #f0f2f5;
        }}
        .btn {{
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .btn-status {{
            background: #e9ecef;
            color: #333;
        }}
        .btn-status:hover {{ background: #dee2e6; }}
        .btn-danger {{ background: #dc3545; color: white; }}
        .btn-secondary {{ background: #6c757d; color: white; }}
        .toast {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 1000;
        }}
        .toast.show {{ transform: translateY(0); opacity: 1; }}
        .toast.success {{ background: #28a745; }}
        .toast.error {{ background: #dc3545; }}
        .delete-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
            z-index: 999;
        }}
        .delete-modal.active {{ display: flex; }}
        .delete-modal .modal-content {{
            background: white;
            padding: 30px;
            border-radius: 16px;
            max-width: 400px;
            text-align: center;
        }}
        .delete-modal .modal-content h2 {{ margin-bottom: 10px; }}
        .delete-modal .modal-content p {{ color: #666; margin-bottom: 20px; }}
        .delete-modal .modal-content .buttons {{ display: flex; gap: 12px; justify-content: center; }}
        @media (max-width: 768px) {{
            .field-row {{ flex-direction: column; align-items: flex-start; gap: 4px; }}
            .field-label {{ width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/admin" class="back-btn">← Назад к списку</a>

        <div class="order-card">
            <div class="order-header">
                <h1>📋 Заказ <span>#{order_number}</span></h1>
                <span class="status-badge {status_class}">{status_emoji} {status_name}</span>
            </div>

            <div class="order-fields">
                {fields_html}
            </div>

            <div class="actions">
                {status_buttons}
                <button class="btn btn-danger" onclick="showDeleteModal()">🗑️ Удалить</button>
                <a href="/admin" class="btn btn-secondary">🔙 Назад</a>
            </div>
        </div>
    </div>

    <div class="delete-modal" id="deleteModal">
        <div class="modal-content">
            <h2>⚠️ Удалить заказ?</h2>
            <p>Вы уверены, что хотите удалить заказ #{order_number}? Это действие нельзя отменить.</p>
            <div class="buttons">
                <button class="btn btn-danger" onclick="deleteOrder()">Да, удалить</button>
                <button class="btn btn-secondary" onclick="hideDeleteModal()">Отмена</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        const orderNumber = '{order_number}';

        // Редактирование полей
        document.querySelectorAll('.field-value input').forEach(input => {{
            const display = document.getElementById('display_' + input.dataset.field);

            display.addEventListener('dblclick', function() {{
                this.classList.add('hidden');
                input.classList.add('active');
                input.focus();
                input.select();
            }});

            input.addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') {{
                    saveField(this.dataset.field, this.value);
                }}
                if (e.key === 'Escape') {{
                    this.value = display.textContent;
                    this.classList.remove('active');
                    display.classList.remove('hidden');
                }}
            }});

            input.addEventListener('blur', function() {{
                if (this.classList.contains('active')) {{
                    saveField(this.dataset.field, this.value);
                }}
            }});
        }});

        async function saveField(field, value) {{
            const display = document.getElementById('display_' + field);
            const input = document.getElementById('input_' + field);

            try {{
                const response = await fetch(`/api/orders/${{orderNumber}}/field`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ field, value }})
                }});

                const data = await response.json();

                if (data.success) {{
                    display.textContent = value;
                    input.value = value;
                    showToast('✅ Поле обновлено', 'success');
                }} else {{
                    showToast('❌ Ошибка обновления', 'error');
                }}
            }} catch (error) {{
                showToast('❌ Ошибка соединения', 'error');
            }}

            input.classList.remove('active');
            display.classList.remove('hidden');
        }}

        async function updateStatus(status) {{
            try {{
                const response = await fetch(`/api/orders/${{orderNumber}}/status`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ status }})
                }});

                const data = await response.json();

                if (data.success) {{
                    showToast(`✅ Статус обновлён`, 'success');
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    showToast('❌ Ошибка обновления статуса', 'error');
                }}
            }} catch (error) {{
                showToast('❌ Ошибка соединения', 'error');
            }}
        }}

        function showDeleteModal() {{
            document.getElementById('deleteModal').classList.add('active');
        }}

        function hideDeleteModal() {{
            document.getElementById('deleteModal').classList.remove('active');
        }}

        async function deleteOrder() {{
            try {{
                const response = await fetch(`/api/orders/${{orderNumber}}`, {{
                    method: 'DELETE'
                }});

                const data = await response.json();

                if (data.success) {{
                    showToast('🗑️ Заказ удалён', 'success');
                    setTimeout(() => {{
                        window.location.href = '/admin';
                    }}, 1000);
                }} else {{
                    showToast('❌ Ошибка удаления', 'error');
                }}
            }} catch (error) {{
                showToast('❌ Ошибка соединения', 'error');
            }}

            hideDeleteModal();
        }}

        function showToast(message, type) {{
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type + ' show';
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 3000);
        }}
    </script>
</body>
</html>
    '''


def render_courier_index(orders: List[Dict], error: str = None) -> str:
    """Страница курьера - все заказы."""
    cards = ''
    for order in orders:
        status = order.get('status', 'new')
        status_class = get_status_class(status)
        status_name = STATUS_NAMES.get(status, status)
        status_emoji = STATUS_EMOJIS.get(status, '📋')
        address = order.get('address', '—')
        if len(address) > 30:
            address = address[:30] + '...'

        cards += f'''
        <a href="/courier/order/{order.get('order_number')}" class="order-card">
            <div class="order-number">📦 Заказ <span>#{order.get('order_number', '—')}</span></div>
            <div class="info">
                <div class="row">
                    <span class="label">Адрес</span>
                    <span>{address}</span>
                </div>
                <div class="row">
                    <span class="label">Телефон</span>
                    <span>{order.get('phone', '—')}</span>
                </div>
                <div class="row">
                    <span class="label">Статус</span>
                    <span class="status {status_class}">{status_emoji} {status_name}</span>
                </div>
            </div>
        </a>
        '''

    error_html = f'<div class="error-msg">{error}</div>' if error else ''
    no_orders_html = '''
        <div class="no-orders">
            <span class="emoji">📭</span>
            Нет заказов
        </div>
    ''' if not orders else ''

    return f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Курьерская панель</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header p {{ opacity: 0.9; font-size: 16px; }}
        .orders-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}
        .order-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
        }}
        .order-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        }}
        .order-card .order-number {{ font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px; }}
        .order-card .order-number span {{ color: #28a745; }}
        .order-card .info {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }}
        .order-card .info .row {{ display: flex; justify-content: space-between; font-size: 14px; color: #555; }}
        .order-card .info .row .label {{ color: #999; }}
        .order-card .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }}
        .status-new {{ background: #fff3cd; color: #856404; }}
        .status-collecting {{ background: #cce5ff; color: #004085; }}
        .status-ready {{ background: #d4edda; color: #155724; }}
        .status-delivering {{ background: #fff3cd; color: #856404; }}
        .status-delivered {{ background: #e2e3e5; color: #383d41; }}
        .no-orders {{ text-align: center; padding: 60px 20px; color: #999; font-size: 18px; }}
        .no-orders .emoji {{ font-size: 64px; display: block; margin-bottom: 20px; }}
        .error-msg {{
            background: #f8d7da;
            color: #721c24;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
        }}
        @media (max-width: 768px) {{
            .orders-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚚 Курьерская панель</h1>
            <p>Все заказы</p>
        </div>

        {error_html}

        <div class="orders-grid">
            {cards}
        </div>
        {no_orders_html}
    </div>
</body>
</html>
    '''


def render_courier_order(order: Dict, order_number: str) -> str:
    """Страница курьера - детали заказа с кнопкой Доставлен."""
    status = order.get('status', 'new')
    status_class = get_status_class(status)
    status_name = STATUS_NAMES.get(status, status)
    status_emoji = STATUS_EMOJIS.get(status, '📋')

    fields = [
        ('📍 Адрес', order.get('address', '—')),
        ('🕐 Время', order.get('time_interval', '—')),
        ('📱 Телефон', order.get('phone', '—')),
        ('💰 Сумма', order.get('amount', '—')),
        ('📝 Комментарий', order.get('comment', '—')),
    ]

    fields_html = ''
    for label, value in fields:
        fields_html += f'''
        <div class="field-row">
            <span class="field-label">{label}</span>
            <div class="field-value">{value}</div>
        </div>
        '''

    # Кнопка "Доставлен" показывается всегда, кроме статуса "Доставлен"
    deliver_button = ''
    if status != 'delivered':
        deliver_button = f'''
        <button class="btn btn-success" onclick="updateStatus('delivered')">
            ✅ Доставлен
        </button>
        '''

    return f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Заказ #{order_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            padding: 20px;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .back-btn {{
            display: inline-block;
            margin-bottom: 20px;
            color: #28a745;
            text-decoration: none;
            font-weight: 500;
        }}
        .back-btn:hover {{ text-decoration: underline; }}
        .order-card {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .order-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f2f5;
        }}
        .order-header h1 {{ font-size: 24px; }}
        .order-header h1 span {{ color: #28a745; }}
        .status-badge {{
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }}
        .status-new {{ background: #fff3cd; color: #856404; }}
        .status-collecting {{ background: #cce5ff; color: #004085; }}
        .status-ready {{ background: #d4edda; color: #155724; }}
        .status-delivering {{ background: #fff3cd; color: #856404; }}
        .status-delivered {{ background: #e2e3e5; color: #383d41; }}
        .order-fields {{ display: flex; flex-direction: column; gap: 16px; margin-bottom: 30px; }}
        .field-row {{
            display: flex;
            align-items: center;
            padding: 12px 16px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .field-label {{ width: 140px; font-weight: 500; color: #555; flex-shrink: 0; }}
        .field-value {{ flex: 1; color: #333; }}
        .actions {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            padding-top: 20px;
            border-top: 2px solid #f0f2f5;
        }}
        .btn {{
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .btn-success {{ background: #28a745; color: white; }}
        .btn-secondary {{ background: #6c757d; color: white; }}
        .toast {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 1000;
        }}
        .toast.show {{ transform: translateY(0); opacity: 1; }}
        .toast.success {{ background: #28a745; }}
        .toast.error {{ background: #dc3545; }}
        .telegram-link {{
            margin-top: 20px;
            padding: 15px;
            background: #e8f5e9;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #c8e6c9;
        }}
        .telegram-link a {{
            color: #28a745;
            text-decoration: none;
            font-weight: 500;
        }}
        .telegram-link a:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{
            .field-row {{ flex-direction: column; align-items: flex-start; gap: 4px; }}
            .field-label {{ width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="order-card">
            <div class="order-header">
                <h1>📦 Заказ <span>#{order_number}</span></h1>
                <span class="status-badge {status_class}">{status_emoji} {status_name}</span>
            </div>

            <div class="order-fields">
                {fields_html}
            </div>

            <div class="actions">
                {deliver_button}
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        const orderNumber = '{order_number}';

        async function updateStatus(status) {{
            try {{
                const response = await fetch(`/api/orders/${{orderNumber}}/status`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ status }})
                }});

                const data = await response.json();

                if (data.success) {{
                    showToast('✅ Заказ отмечен как доставленный!', 'success');
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    showToast('❌ Ошибка обновления статуса', 'error');
                }}
            }} catch (error) {{
                showToast('❌ Ошибка соединения', 'error');
            }}
        }}

        function showToast(message, type) {{
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type + ' show';
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 3000);
        }}
    </script>
</body>
</html>
    '''


# === API ЭНДПОИНТЫ ===

@app.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request):
    orders = get_all_orders()
    return HTMLResponse(content=render_admin_index(orders))


@app.get("/admin/order/{order_number}", response_class=HTMLResponse)
async def admin_order(request: Request, order_number: str):
    order = get_order_by_number(order_number)
    if not order:
        orders = get_all_orders()
        return HTMLResponse(content=render_admin_index(orders, error=f"Заказ #{order_number} не найден"))
    return HTMLResponse(content=render_admin_order(order, order_number))


@app.get("/courier", response_class=HTMLResponse)
async def courier_index(request: Request):
    orders = get_all_orders()
    return HTMLResponse(content=render_courier_index(orders))


@app.get("/courier/order/{order_number}", response_class=HTMLResponse)
async def courier_order(request: Request, order_number: str):
    order = get_order_by_number(order_number)
    if not order:
        orders = get_all_orders()
        return HTMLResponse(content=render_courier_index(orders, error=f"Заказ #{order_number} не найден"))

    return HTMLResponse(content=render_courier_order(order, order_number))


@app.get("/api/orders")
async def get_orders():
    return {"orders": get_all_orders()}


@app.get("/api/orders/{order_number}")
async def get_order(order_number: str):
    order = get_order_by_number(order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@app.post("/api/orders/{order_number}/field")
async def update_order_field_api(order_number: str, data: OrderFieldUpdate):
    if not update_order_field(order_number, data.field, data.value):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return {"success": True, "message": "Поле обновлено"}


@app.post("/api/orders/{order_number}/status")
async def update_order_status_api(order_number: str, data: OrderStatusUpdate):
    if not update_order_status(order_number, data.status):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return {"success": True, "message": "Статус обновлён"}


@app.delete("/api/orders/{order_number}")
async def delete_order_api(order_number: str):
    if not delete_order(order_number):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return {"success": True, "message": "Заказ удалён"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)