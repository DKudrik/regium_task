from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///avito.db")
Base = declarative_base(bind=engine)


class Advertisement(Base):
    __tablename__ = "advertisements"
    advt_id = Column(Integer, primary_key=True)
    price = Column(Integer)
    price_eur = Column(Float)
    year = Column(Integer)
    mileage = Column(Integer)
    engine_volume = Column(Float)
    transmission = Column(String(2))
    horse_power = Column(Float)
    drive_wheels = Column(String(20))
    fuel = Column(String(20))
    is_market_price = Column(Boolean)
    is_only_on_avito = Column(Boolean)
    is_owner = Column(Boolean)
    is_damaged = Column(Boolean)
    description = Column(String(500))
    place_of_sale = Column(String(50))
    url_to_advt_page = Column(String(100))
    created = Column(String(50))

    def __init__(
        self,
        advt_id,
        price,
        price_eur,
        year,
        mileage,
        engine_volume,
        transmission,
        horse_power,
        drive_wheels,
        fuel,
        is_market_price,
        is_only_on_avito,
        is_owner,
        is_damaged,
        description,
        place_of_sale,
        url_to_advt_page,
        created,
    ):
        self.advt_id = advt_id
        self.price = price
        self.price_eur = price_eur
        self.year = year
        self.mileage = mileage
        self.engine_volume = engine_volume
        self.transmission = transmission
        self.horse_power = horse_power
        self.drive_wheels = drive_wheels
        self.fuel = fuel
        self.is_market_price = is_market_price
        self.is_only_on_avito = is_only_on_avito
        self.is_owner = is_owner
        self.is_damaged = is_damaged
        self.description = description
        self.place_of_sale = place_of_sale
        self.url_to_advt_page = url_to_advt_page
        self.created = created


def create_db():
    Base.metadata.create_all()
    session = sessionmaker(bind=engine)
    s = session()
    return s
