"""Proyectos de ejemplo (PHP al estilo Laravel, Node con Express y SQL, Python con Flask y SQLAlchemy) para probar documentar.py."""
import os
import shutil
import stat
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / ".temporal" / "proy-documentar"


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def escribir(raiz, rel, texto):
    f = raiz / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto.lstrip("\n"), encoding="utf-8", newline="\n")


def php():
    r = BASE / "php"
    escribir(r, "composer.json", r'''{
    "name": "demo/tienda",
    "require": {
        "php": "^8.1",
        "laravel/framework": "^10.0",
        "laravel/sanctum": "^3.2"
    },
    "require-dev": {
        "phpunit/phpunit": "^10.0"
    },
    "autoload": {
        "psr-4": {
            "App\\": "app/"
        }
    }
}
''')
    escribir(r, ".env.example", "APP_NAME=Tienda\nDB_HOST=127.0.0.1\nDB_DATABASE=tienda\nMAIL_FROM=ventas@example.com\n")
    escribir(r, "app/Models/User.php", r'''<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class User extends Model
{
    public function pedidos()
    {
        return $this->hasMany(Pedido::class);
    }

    public function isAdmin()
    {
        return $this->role === 'admin';
    }

    private function normalizar($nombre)
    {
        return trim($nombre);
    }
}
''')
    escribir(r, "app/Models/Pedido.php", r'''<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Pedido extends Model
{
    const ESTADO_PENDIENTE = 'pendiente';
    const ESTADO_PAGADO = 'pagado';

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function total()
    {
        return $this->items->sum('subtotal');
    }
}
''')
    escribir(r, "app/Models/Producto.php", r'''<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Producto extends Model
{
    public function precioFinal()
    {
        return $this->precio * 1.21;
    }
}
''')
    escribir(r, "app/Http/Controllers/Controller.php", r'''<?php
namespace App\Http\Controllers;

class Controller
{
}
''')
    escribir(r, "app/Http/Controllers/PedidoController.php", r'''<?php
namespace App\Http\Controllers;

use App\Models\Pedido;
use App\Services\Facturador;

class PedidoController extends Controller
{
    public function index()
    {
        return Pedido::all();
    }

    public function store($request)
    {
        $request->validate([
            'cantidad' => 'required|integer|min:1|max:100',
            'producto_id' => 'required|exists:productos,id',
        ]);
        $pedido = Pedido::create($request->all());
        if (!auth()->user()->can('crear-pedido')) {
            abort(403);
        }
        return (new Facturador())->facturar($pedido);
    }
}
''')
    escribir(r, "app/Services/Facturador.php", r'''<?php
namespace App\Services;

use App\Models\Pedido;

class Facturador
{
    const IVA = 21;

    public function facturar(Pedido $pedido)
    {
        $total = $pedido->total();
        if ($total > 1000) {
            $descuento = 0.1;
        }
        return $total * (1 + self::IVA / 100) - ($descuento ?? 0);
    }
}
''')
    escribir(r, "routes/web.php", r'''<?php
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\PedidoController;

Route::get('/pedidos', [PedidoController::class, 'index']);
Route::post('/pedidos', [PedidoController::class, 'store']);
Route::get('/salud', function () {
    return 'ok';
});
''')
    escribir(r, "database/migrations/2024_01_01_000000_create_users_table.php", r'''<?php
use Illuminate\Support\Facades\Schema;

return new class {
    public function up()
    {
        Schema::create('users', function ($table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->string('role');
            $table->timestamps();
        });
    }
};
''')
    escribir(r, "database/migrations/2024_01_02_000000_create_pedidos_table.php", r'''<?php
use Illuminate\Support\Facades\Schema;

return new class {
    public function up()
    {
        Schema::create('pedidos', function ($table) {
            $table->id();
            $table->foreignId('user_id')->constrained();
            $table->string('estado');
            $table->decimal('total', 10, 2);
        });
    }
};
''')
    escribir(r, "database/migrations/2024_01_03_000000_create_productos_table.php", r'''<?php
use Illuminate\Support\Facades\Schema;

return new class {
    public function up()
    {
        Schema::create('productos', function ($table) {
            $table->id();
            $table->string('nombre');
            $table->decimal('precio', 10, 2);
        });
        Schema::create('pedido_producto', function ($table) {
            $table->foreignId('pedido_id')->constrained();
            $table->foreignId('producto_id')->constrained();
            $table->integer('cantidad');
        });
    }
};
''')
    escribir(r, "tests/Feature/PedidoTest.php", "<?php\nclass PedidoTest {}\n")
    return r


def js():
    r = BASE / "js"
    escribir(r, "package.json", '''{
  "name": "api-pedidos",
  "dependencies": {
    "express": "^4.18.0",
    "pg": "^8.11.0",
    "jsonwebtoken": "^9.0.0"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "typescript": "^5.0.0"
  }
}
''')
    escribir(r, ".env.example", "PORT=3000\nDATABASE_URL=postgres://localhost/pedidos\nJWT_SECRET=cambiar\n")
    escribir(r, "schema.sql", '''CREATE TABLE clientes (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  email VARCHAR(120) UNIQUE
);

CREATE TABLE pedidos (
  id SERIAL PRIMARY KEY,
  cliente_id INTEGER NOT NULL REFERENCES clientes(id),
  total NUMERIC(10,2),
  estado VARCHAR(20)
);

CREATE TABLE items (
  id SERIAL PRIMARY KEY,
  pedido_id INTEGER,
  producto VARCHAR(80),
  cantidad INTEGER,
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
);
''')
    escribir(r, "src/app.js", '''const express = require('express');
const pedidos = require('./routes/pedidos');

const app = express();
app.use('/api', pedidos);
app.listen(process.env.PORT || 3000);
''')
    escribir(r, "src/routes/pedidos.js", '''const { Router } = require('express');
const { Facturador } = require('../services/facturacion');
const { validarPedido } = require('../utils/validar');

const router = Router();

router.get('/pedidos', listar);
router.post('/pedidos', (req, res) => {
  validarPedido(req.body);
  res.json(new Facturador().facturar(req.body));
});

function listar(req, res) {
  res.json([]);
}

module.exports = router;
''')
    escribir(r, "src/services/facturacion.js", '''const { Pedido } = require('../models/pedido');

class Facturador {
  facturar(datos) {
    const pedido = new Pedido(datos);
    const total = pedido.total();
    if (total > 5000) {
      return total * 0.9;
    }
    return total;
  }

  async enviar(factura) {
    return factura;
  }
}

module.exports = { Facturador };
''')
    escribir(r, "src/models/pedido.js", '''class Pedido {
  constructor(datos) {
    this.items = datos.items || [];
  }

  total() {
    return this.items.reduce((s, i) => s + i.cantidad, 0);
  }
}

module.exports = { Pedido };
''')
    escribir(r, "src/models/cliente.js", '''class Cliente {
  constructor(nombre) {
    this.nombre = nombre;
  }
}

class ClienteVip extends Cliente {
  descuento() {
    return 0.15;
  }
}

module.exports = { Cliente, ClienteVip };
''')
    escribir(r, "src/utils/validar.js", '''function validarPedido(datos) {
  if (!datos.items || datos.items.length > 50) {
    throw new Error('pedido inválido');
  }
}

module.exports = { validarPedido };
''')
    escribir(r, "tests/facturacion.test.js", "test('x', () => {});\n")
    return r


def py():
    r = BASE / "py"
    escribir(r, "requirements.txt", "flask==3.0.0\nflask-sqlalchemy==3.1.1\npytest==8.0.0\ncelery==5.3.0\n")
    escribir(r, ".env.example", "SECRET_KEY=cambiar\nDATABASE_URL=sqlite:///app.db\n")
    escribir(r, "app/__init__.py", '''import os
from flask import Flask
from .routes import bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.register_blueprint(bp)
    return app
''')
    escribir(r, "app/models.py", '''from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Cliente(db.Model):
    __tablename__ = "clientes"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80))
    email = db.Column(db.String(120))

    def nombre_completo(self):
        return self.nombre


class Pedido(db.Model):
    __tablename__ = "pedidos"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    monto = db.Column(db.Numeric)
    estado = db.Column(db.String(20))
''')
    escribir(r, "app/routes.py", '''from flask import Blueprint, request
from .services.facturacion import Facturador

bp = Blueprint("pedidos", __name__)


@bp.route("/pedidos", methods=["GET", "POST"])
def pedidos():
    if request.method == "POST":
        return Facturador().facturar(request.json)
    return []


@bp.get("/salud")
def salud():
    return "ok"
''')
    escribir(r, "app/services/__init__.py", "")
    escribir(r, "app/services/facturacion.py", '''from ..models import Pedido

LIMITE_CREDITO = 2500


class Facturador:
    def facturar(self, datos):
        monto = datos["monto"]
        if monto > 1000:
            monto = monto * 0.95
        return monto

    def _redondear(self, valor):
        return round(valor, 2)


class FacturadorExento(Facturador):
    def facturar(self, datos):
        return datos["monto"]
''')
    escribir(r, "app/utils.py", "def limpiar(texto):\n    return texto.strip()\n")
    escribir(r, "tests/test_facturacion.py", "def test_x():\n    assert True\n")
    return r


def crear_todo():
    if BASE.exists():
        shutil.rmtree(BASE, onerror=_forzar)
    BASE.mkdir(parents=True)
    return {"php": php(), "js": js(), "py": py()}


if __name__ == "__main__":
    for nombre, ruta in crear_todo().items():
        print(nombre, ruta)
