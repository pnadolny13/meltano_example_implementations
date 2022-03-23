with source as (

    {#-
    Normally we would select from the table here, but we are using seeds to load
    our data in this project
    #}
    select * from {{ source('tap_csv', 'orders') }}

),

renamed as (

    select
        id::int as order_id,
        user_id::int as customer_id,
        order_date::date,
        status

    from source

)

select * from renamed
