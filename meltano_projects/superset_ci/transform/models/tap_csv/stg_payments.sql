with source as (
    
    {#-
    Normally we would select from the table here, but we are using seeds to load
    our data in this project
    #}
    select * from {{ source('tap_csv', 'payments') }}

),

renamed as (

    select
        id::int as payment_id,
        order_id::int,
        payment_method,

        -- `amount` is currently stored in cents, so we convert it to dollars
        amount::int / 100 as amount

    from source

)

select * from renamed
