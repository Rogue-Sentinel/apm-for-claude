# The anti-corruption layer

## What it is

An anti-corruption layer is a translation boundary between your domain and an outside system. It
keeps the outside system's model, names and conventions from leaking into your domain.

```
[ outside system ]  <-->  [ anti-corruption layer: adapter + mapper ]  <-->  [ domain ]
```

## 1. Adapter and mapper

The adapter implements a domain port; the mapper translates between the two models.

```
// the domain's port
interface InventoryService:
    checkStock(productId: ProductId) -> StockLevel

// the outside system answers in its own model:
// { "sku": "ABC-123", "qty_available": 42, "warehouse_code": "US-WEST" }

// the anti-corruption layer
type ExternalInventoryAdapter implements InventoryService:
    constructor(client: ExternalInventoryClient)
    checkStock(productId):
        response = client.getInventory(productId.toSku())
        return InventoryMapper.toDomain(response)

type InventoryMapper:
    toDomain(response) -> StockLevel:
        return new StockLevel(response.qty_available, Warehouse.from(response.warehouse_code))
```

## 2. Separate models at each boundary

Use different models for what comes in and what goes out.

```
// inbound: the API's request becomes a domain command
type CreateOrderRequest:                 // the API's model
    items: list of { sku: text, qty: number }
    customer_email: text

type CreateOrderCommand:                 // the domain's command
    items: list of OrderItem
    customerEmail: EmailAddress

function toCommand(request: CreateOrderRequest) -> CreateOrderCommand:
    return new CreateOrderCommand(
        request.items.map(i -> new OrderItem(ProductId.from(i.sku), Quantity.of(i.qty))),
        EmailAddress.of(request.customer_email))

// outbound: a domain entity becomes a stored record
type OrderPersistenceMapper:
    toRow(order: Order) -> OrderRow
    toDomain(row: OrderRow) -> Order
```

Construction is also validation: `EmailAddress.of` and `Quantity.of` refuse bad input (returning a
result, `apm:functional-core`), so nothing invalid crosses into the domain.

## 3. A facade over a complicated outside system

Hide a complicated outside API behind the one operation your domain needs.

```
// the outside API: many steps
type ThirdPartyShippingApi:
    createShipment(data)
    addPackage(shipmentId, package)
    setOrigin(shipmentId, address)
    setDestination(shipmentId, address)
    calculateRate(shipmentId)
    confirmShipment(shipmentId)

// your facade: one domain operation
type ShippingAdapter implements ShippingService:
    quote(origin, destination, packages) -> ShippingQuote:
        id = api.createShipment({})
        api.setOrigin(id, mapAddress(origin))
        api.setDestination(id, mapAddress(destination))
        for package in packages: api.addPackage(id, mapPackage(package))
        rate = api.calculateRate(id)
        return new ShippingQuote(Money.of(rate.total), rate.estimatedDays)
```

## Mapping strategies

| Strategy | When |
|----------|------|
| Hand-written mapping | simple models, few fields, full control |
| Extension functions | where the language has them: keeps the mapper next to the type without putting it inside the domain |
| A mapping library | many models with similar shapes, to cut boilerplate |
| Mapping through the constructor | the target type validates as it is built |

## Boundary rules

1. **Outside types never cross into the domain.**
2. **Domain types never cross outward past the infrastructure boundary.**
3. **Each boundary has its own model**, even when the models look alike.
4. **Mappers live on the infrastructure side**, not inside the domain.
5. **The domain sets the vocabulary**; the outside systems are adapted to it.
